# Proof of concept Python mp3 decoder

Most ways of decoding mp3s seem to require using something from the command line like `ffmpeg` or `lame`, and ways of doing it in Python seem to mostly rely on using these programs and calling `subprocess` or something similar.

This is a simple library to just take an mp3 from any kind of chunked iterator (from a file, from a http stream, from an encoder...) and outputs it in raw pcm format in chunks. This is by no means a complete implementation of an mp3 decoder but it seems to work on a lot of mp3 files tested. It can handle VBR.

Decoding mp3 data results in more data than was passed in, buffers need to be appropriately sized. Some empirical testing reveals that the decoded pcm data can be up to 15 times larger than the input chunk - take this into account!

## Dependencies

- swig3.0 to generate a C interface (using swig means that it doesn't rely on numpy and hence is a lot more portable).
- libmp3lame with development headers

## Example

In these examples I'm using PyAudio because it has good support for streaming chunks of data.

After constructing a Decoder object with an appropriately sized pcm buffer size, passing a iterable of chunked content to decode into `decode_iter` will return a generator which yields decoded data.

A somewhat convoluted example using a buffered io file:

```python
from pymp3decoder import Decoder
CHUNK_SIZE = 4096

import io
import pyaudio

# initialise decoder
decoder = Decoder(CHUNK_SIZE*20)

# initialise pyaudio
p = pyaudio.PyAudio()

stream = p.open(format=p.get_format_from_width(2),
                channels=2,
                rate=44100,
                output=True)


def read_chunk(file_buffer):
    """ Read chunks from a file """

    while 1:
        content = file_buffer.read(CHUNK_SIZE)

        if content:
            yield content
        else:
            return

# open file and read in chunks
with io.open("example.mp3", "rb", buffering=CHUNK_SIZE) as in_file:
    for chunk in decoder.decode_iter(read_chunk(in_file)):
        stream.write(chunk)

stream.stop_stream()
stream.close()

p.terminate()
```

A much more sensible example is the case of downloading mp3 data with requests:

```python
from pymp3decoder import Decoder
CHUNK_SIZE = 4096

import requests

decoder = Decoder(CHUNK_SIZE*20)
remote_mp3 = requests.get("http://localhost:8000/example.mp3")

def take_chunk(content):
    """ Split a buffer of data into chunks """

    num_blocks = int(math.ceil(1.0*len(content)/CHUNK_SIZE))

    for start in range(num_blocks):
        yield content[CHUNK_SIZE*start:CHUNK_SIZE*(start+1)]

for chunk in decoder.decode_iter(take_chunk(remote_mp3.content)):
    ...
```

Or streaming it:

```python
from pymp3decoder import Decoder
CHUNK_SIZE = 4096

import requests

decoder = Decoder(CHUNK_SIZE*20)
remote_mp3 = requests.get("http://localhost:8000/example.mp3", stream=True)

for chunk in decoder.decode_iter(remote_mp3.iter_content(chunk_size=CHUNK_SIZE)):
    ...
```

More examples are in the `examples/` subfolder.

## Tests

Running `python setup.py test` should use the decoder to play an example track of some durmming. This does require PyAudio, which in turn requires PortAudio.

## License

MIT
