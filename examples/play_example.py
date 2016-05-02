from pymp3decoder import Decoder
import contextlib
import io
import math

import pyaudio

CHUNK_SIZE = 4096


def read_chunk(file_buffer):
    """ Read chunks from a file """

    while 1:
        content = file_buffer.read(CHUNK_SIZE)

        if content:
            yield content
        else:
            return


def take_chunk(content):
    """ Split a buffer of data into chunks """

    num_blocks = int(math.ceil(1.0*len(content)/CHUNK_SIZE))

    for start in xrange(num_blocks):
        yield content[CHUNK_SIZE*start:CHUNK_SIZE*(start+1)]


class ExamplePlayer:
    @contextlib.contextmanager
    def start(self):
        try:
            p = pyaudio.PyAudio()

            self.decoder = Decoder(CHUNK_SIZE*20)

            self.stream = p.open(format=p.get_format_from_width(2),
                                 channels=2,
                                 rate=44100,
                                 output=True)

            yield self.stream
        finally:
            self.stream.stop_stream()
            self.stream.close()

            p.terminate()


    def example_file(self):
        """ Open a file and decode it """

        with open("example.mp3", "rb") as in_file, self.start():
            content = in_file.read()

            for chunk in self.decoder.decode_iter(take_chunk(content)):
                self.stream.write(chunk)


    def example_file_stream(self):
        """ Open a file in buffered mode and read/decode a chunk at a time """

        with io.open("example.mp3", "rb", buffering=CHUNK_SIZE) as in_file, self.start():
            for chunk in self.decoder.decode_iter(read_chunk(in_file)):
                self.stream.write(chunk)


    def example_tcp_stream(self):
        """ Stream an mp3 from a url and decode it """

        import requests
        remote_mp3 = requests.get("http://localhost:8000/example.mp3", stream=True)

        for chunk in self.decoder.decode_iter(take_chunk(remote_mp3)), self.start():
            self.stream.write(chunk)
