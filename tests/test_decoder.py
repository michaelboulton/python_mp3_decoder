from pymp3decoder import Decoder
import contextlib
import os
import math

import pyaudio

CHUNK_SIZE = 4096


def take_chunk(content):
    """ Split a buffer of data into chunks """

    num_blocks = int(math.ceil(1.0*len(content)/CHUNK_SIZE))

    for start in range(num_blocks):
        yield content[CHUNK_SIZE*start:CHUNK_SIZE*(start+1)]


class TestPlayer:
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


    def test_file(self):
        """ Open a file and decode it """

        abs_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.mp3")

        with open(abs_location, "rb") as in_file, self.start():
            content = in_file.read()

            for chunk in self.decoder.decode_iter(take_chunk(content)):
                self.stream.write(chunk)
