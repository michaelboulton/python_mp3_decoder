import pymp3_c
import struct


def get_pad(bn):
    return "{:0>8b}".format(bn)


class Decoder(object):

    # mapping frame header byte to bit rate of frame
    # FIXME can be mopved into an array easily
    bitrate_table = {
        0b00010000: 32,
        0b00100000: 40,
        0b00110000: 48,
        0b01000000: 56,
        0b01010000: 64,
        0b01100000: 80,
        0b01110000: 96,
        0b10000000: 112,
        0b10010000: 128,
        0b10100000: 160,
        0b10110000: 192,
        0b11000000: 224,
        0b11010000: 256,
        0b11100000: 320,
    }

    sample_rate_table = {
        0b00: 44100,
        0b01: 48000,
        0b10: 32000,
    }

    def __init__(self, pcm_buf_size):
        """ Initialise decoder

        pcm_buf_size needs to be set to a value that will be big enough to hold
        all of the decoded pcm data or it'll probably seg fault. From some
        empirical testing, making sure that the pcm buffer size is at least 8-10
        times bigger than the size of each input chunk, it should be fine. 15
        times bigger is a safe bet.

        Args:
            pcm_buf_size (int): size of internal pcm buffer in bytes
        """

        self.pcm_l = bytearray([0]*pcm_buf_size)
        self.pcm_r = bytearray([0]*pcm_buf_size)

        self.joined = bytearray([0]*pcm_buf_size*2)

        self.decoder = pymp3_c.LameDecoder()

    def get_tag_length(self, mp3_buffer):
        """ Get tag length of ID3v2 header

        Just checks to see if there is a header in this chunk, and if so read
        the synchsafe integer in the 6-10th bytes to get the total header
        length.

        Args:
            mp3_buffer (bytes): string corresponding to a chunk of raw mp3 data
        Returns:
            header_length (int): Length of ID3v2 header
        """

        unpacked = struct.unpack("BBBxxBBBBB", mp3_buffer[:10])

        if not all(i == j for i, j in zip(unpacked[:3], (ord(i) for i in "ID3"))):
            # no tag found
            return 0

        # this byte is id3v2 flags
        flags = unpacked[3]

        # TODO will need to handle these if it ever comes up I suppose
        if flags & 0b01000000:
            # extended header
            pass
        if flags & 0b00010000:
            # extended footer
            pass

        # find size of header from synchsafe integer
        header_size_bytes = unpacked[4:10]
        unsquished = [get_pad(x)[1:] for x in header_size_bytes]
        unsquished = "".join(unsquished)
        unsquished = int(unsquished, 2)

        # TODO
        # there's lots more to the header...this works for 90% of stuff
        # http://id3.org/id3v2.4.0-structure

        # + 10 for extra padding
        return unsquished + 10

    def decode(self, mp3_data, remaining):
        """ Takes an mp3 buffer and decodes it to pcm data

        This expects that the header has already been stripped. Because there is
        almost always going to be half of a frame on the end of a chunk, this is
        not decoded and returned along with the pcm data. When the next chunk is
        passed for decoding, this partial frame is stuck onto the beginning of
        it so that the whole frame can be decoded.

        From original code:

        /*********************************************************************
         * input 1 mp3 frame, output (maybe) pcm data.
         *
         *  nout = hip_decode(hip, mp3buf,len,pcm_l,pcm_r);
         *
         * input:
         *    len          :  number of bytes of mp3 data in mp3buf
         *    mp3buf[len]  :  mp3 data to be decoded
         *
         * output:
         *    nout:  -1    : decoding error
         *            0    : need more data before we can complete the decode
         *           >0    : returned 'nout' samples worth of data in pcm_l,pcm_r
         *    pcm_l[nout]  : left channel data
         *    pcm_r[nout]  : right channel data
         *
         *********************************************************************/

        Looking at the original code, hip_decode, hip_decode1,
        hip_decode1_headers all seem to do the same thing...?

        Args:
            mp3_data (buffer): A buffer of some bytes from the mp3 file to
                decode
            remaining (buffer): A buffer of whatever bytes were left over from a
                previous decoding.

        Returns:
            (pcm_data, remaining): A tuple of the decoded raw pcm data and any
                data that was left over in mp3_data that did not consist of a
                full frame
        """

        # join buffers together
        from_buffer = bytearray(mp3_data)
        mp3_buffer = remaining + from_buffer

        frame_sizes = []
        frame_idx = 0
        frame_num = 0

        #fmt = "Frame {:d} at idx {:d} - header: {:s}"
        #info = "Err protection {}, padded {}"

        # keep going till we run out of frames
        while frame_idx < len(mp3_buffer) - 4:
            frame_header = struct.unpack("BBBB", mp3_buffer[frame_idx:frame_idx+4])

            if frame_header[0] != 255:
                break

            padded = bool(frame_header[2] & 0b10)

            # get the bitrate bits, eg "0b01010000"
            # only care about the top 4
            bitrate_bits = frame_header[2] & 0xf0

            # Makes sure it's an mpeg 1 layer 3
            # remove?
            if (frame_header[1] & 0b00001110) != 0b1010:
                raise RuntimeError("Can currently only handle mpeg 1!")

            sample_bytes = (0b00001100 & frame_header[2]) >> 2
            sample_rate = self.sample_rate_table[sample_bytes]

            # calculate frame size
            frame_size = int(144*(1000*self.bitrate_table[bitrate_bits])/sample_rate)

            if padded:
                frame_size += 1

            # then store them
            frame_sizes.append(frame_size)
            frame_idx = sum(frame_sizes)
            frame_num += 1

        # indexes of beginning of frames in chunk
        frame_indexes = [0]*(len(frame_sizes) + 1)
        for i, _ in enumerate(frame_indexes):
            frame_indexes[i] = sum(frame_sizes[:i])

        # total size of frames, excluding parts of frames that weren't fully included in this chunk
        total_frames_size = sum(frame_sizes)
        # number of bytes left at the end of mp3_data that won't be parsed in this pass
        bytes_left = frame_sizes[-1] - (total_frames_size - len(mp3_buffer))

        # if a frame straddles a boundary, don't include it in the frame indexes
        if bytes_left != 0:
            # if the INDEX of the frame is off the end, then the last frame
            # index will refer to the next frame which is off the end of this
            # chunk, and the second to last refers to the beginning of the
            # partial chunk. we need to strip both the index of the one that
            # isn't in this chunk AND the one in the next chunk
            frame_indexes = frame_indexes[:-2]

        # total number of bytes that have been read so far
        total_samples_read = 0

        try:
            for (begin, size) in zip(frame_indexes, frame_sizes):
                # decode - returns the number of samples read (one sample is 2 bytes)
                samples_read = self.decoder.decode_frame(
                    mp3_buffer,
                    begin,
                    size,
                    total_samples_read,
                    self.pcm_l,
                    self.pcm_r,
                )

                total_samples_read += samples_read
        except ValueError as e:
            raise RuntimeError("Caught exception '{}' - likely cause is that the PCM buffer was not big enough to hold all the decoded data for this frame".format(e))

        pymp3_c.interlace_array(self.pcm_l, self.pcm_r, self.joined, total_samples_read)

        # first multiply by 2 because it's a bytearray and we are returning data
        # in shorts, which are 2 bytes. then, multiply by 2 again because we
        # hace 2 channels worth of data
        decoded_bytes = total_samples_read*2*2

        return self.joined[:decoded_bytes], mp3_buffer[-bytes_left:]

    def decode_iter(self, content):
        """ Decode chunks of content and returns it as dual channel PCM data

        Takes iterable of mp3 data and decodes it in chunks, yielding a chunk of
        raw wav data for each chunk of mp3 data given in.

        Args:
            content (iterable): iterable which yields chunks of mp3 encoded
                data, probably as a generator which returns 4k chunks of
                bytearray data, or a buffer, etc.

        Yields:
            decoded_chunk (bytearray): Chunk of raw wav data in 16 bit dual
                channel mode
        """

        # need to strip the tag off the first chunk
        first_chunk = next(content)
        tag_length = self.get_tag_length(first_chunk)

        # if there is actually a tag
        if tag_length != 0:
            if tag_length < len(first_chunk):
                # if it's smaller than the chunk size, just strip it
                remaining = first_chunk[tag_length:]
            else:
                # if tag header length is bigger than the chunk size, need to
                # keep getting more chunks until it's exchausted
                tag_remaining = tag_length - len(first_chunk)

                # go until tag is exhausted
                while 1:
                    chunk = next(content)
                    tag_remaining -= len(chunk)

                    if tag_remaining < 0:
                        remaining = chunk[tag_remaining:]
                        break
        else:
            remaining = ""

        remaining = bytearray(remaining)

        for chunk in content:
            decoded_chunk, remaining = self.decode(chunk, remaining)
            yield bytes(decoded_chunk)
