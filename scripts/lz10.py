import struct


def decompress_with_original_size(data: bytes) -> tuple[bytes, int]:
  if data[0] != 0x10:
    raise TypeError("This isn't a LZ10-compressed file.")

  decompressed_size = struct.unpack_from("<I", data)[0] >> 8

  out = bytearray(decompressed_size)
  input_pos = 4
  output_pos = 0

  while decompressed_size > 0:
    byte = data[input_pos]
    input_pos += 1

    for bit in range(8):
      if byte & 0x80:
        (temp,) = struct.unpack_from(">H", data, input_pos)
        input_pos += 2

        length = (temp >> 12) + 3
        offset = temp & 0xFFF
        copy_from = output_pos - offset - 1

        for _ in range(length):
          out[output_pos] = out[copy_from]
          output_pos += 1
          copy_from += 1
          decompressed_size -= 1

          if decompressed_size == 0:
            return bytes(out), input_pos

      else:
        out[output_pos] = data[input_pos]
        output_pos += 1
        input_pos += 1
        decompressed_size -= 1

        if decompressed_size == 0:
          return bytes(out), input_pos

      byte <<= 1

  return bytes(out), input_pos


class SearchResult:
  def __init__(self, offset, length):
    self.offset = offset
    self.length = length


def search(window, ahead, distance):
  candidates = []
  for i in range(len(window) - distance):
    if window[i] == ahead[0]:
      candidates.append(i)
  if not candidates:
    return SearchResult(0, 1)
  j = 1
  while j < len(ahead) and candidates:
    k = 0
    while k < len(candidates):
      if window[candidates[k] + j % (len(window) - candidates[k])] != ahead[j] and len(candidates) > 1:
        candidates.pop(k)
        k -= 1
      k += 1
    if len(candidates) < 2:
      j = len(ahead)
    j += 1

  length = 1
  while length < len(ahead) and window[candidates[0] + length % (len(window) - candidates[0])] == ahead[length]:
    length += 1
  return SearchResult(len(window) - candidates[0], length)


def compress(uncompressed_data, read_ahead_buffer_size=3 + 0xF, compression_type=0x10, distance=1):
  output = bytearray()
  uncompressed_size = len(uncompressed_data)

  output.extend(struct.pack("<I", (uncompressed_size << 8) | compression_type))

  original_pos = 0
  while original_pos < uncompressed_size:
    buffer = bytearray()
    byte = 0

    for bit in range(8):
      queue = uncompressed_data[original_pos : original_pos + read_ahead_buffer_size]
      window = uncompressed_data[max(original_pos - 0x1000, 0) : original_pos]

      search_result = search(window, queue, distance)

      if search_result.length > 2:
        byte |= 1 << 7 - bit
        uint = ((search_result.length - 3) << 12) | (search_result.offset - distance)
        buffer.extend(struct.pack(">H", uint))
        original_pos += search_result.length
      else:
        buffer.append(queue[0])
        original_pos += 1

      if original_pos >= uncompressed_size:
        break

    output.append(byte)
    output.extend(buffer)

  return bytes(output)
