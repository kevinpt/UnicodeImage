#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
MIT License

Copyright © 2022 Kevin Thibedeau

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import sys
import argparse
import shutil
from typing import NamedTuple
import numpy as np
import PIL
from PIL import Image, ImageOps

VERSION = '1.0.0'

pil_ver = float('.'.join(PIL.__version__.split('.')[:2]))
assert pil_ver >= 9.2, 'Pillow 9.2 or newer is required'


'''
This script encodes bitmap images into unicode block drawing characters. It uses the
2x2 block characters to improve the horizontal resolution over other methods that only
draw a pair of pixels per char cell in the upper and lower half. There is an added
issue that the pixels in a char cell can have from 1 to 4 unique colors. The 1 and 2
color cases require no intervention but 2x2 blocks with 3 and 4 colors have to be
reduced to 2 to support rendering to a terminal with two colors per cell.

This algorithm always treats the top left pixel in a 2x2 block as the foreground
color. The other three pixels are evaluated to decide which block character matches
their pattern.

  [tl][tr]  [*][ ] --> ▚
  [bl][br]  [ ][*]
'''

class BlockSize(NamedTuple):
  w: int
  h: int


# Characters ordered to form a binary code sequence from (tl<<3 | tr<<2 | bl<<1 | br)
unicode_2x2   = ' ▗▖▄▝▐▞▟▘▚▌▙▀▜▛█'
cp437_2x2     = '   ▄ ▐▄▄ ▀▌▄▀▀▀█'
cp437_2x2_inv = '███▀█▌▀▀█▄▐▀▄▄▄ '


# ANSI foreground colors (background is fg + 10)
# RGB triplets from xterm colors
ansi_pal_map = {
  (0,0,0):       30,
  (205,0,0):     31,
  (0,205,0):     32,
  (205,205,0):   33,
  (0,0,238):     34,
  (205,0,205):   35,
  (0,205,205):   36,
  (229,229,229): 37,
  (127,127,127): 90,
  (255,0,0):     91,
  (0,255,0):     92,
  (255,255,0):   93,
  (92,92,255):   94,
  (255,0,255):   95,
  (0,255,255):   96,
  (255,255,255): 97
}

ansi_pal_rev_map = dict(reversed(i) for i in ansi_pal_map.items())

# Build palette image for quantization
ansi_pal = Image.new('P', (1,1))
ansi_pal.putpalette([n for s in ansi_pal_map.keys() for n in s])


# ANSI 256 color palette

ansi256_pal_vals = (
# Lower 16 colors are system dependent so we skip them
#  (0,0,0),        (128,0,0),      (0,128,0),      (128,128,0),
#  (0,0,128),      (128,0,128),    (0,128,128),    (192,192,192),
#  (128,128,128),  (255,0,0),      (0,255,0),      (255,255,0),
#  (0,0,255),      (255,0,255),    (0,255,255),    (255,255,255),
  (0,0,0),        (0,0,95),       (0,0,135),      (0,0,175),
  (0,0,215),      (0,0,255),      (0,95,0),       (0,95,95),
  (0,95,135),     (0,95,175),     (0,95,215),     (0,95,255),
  (0,135,0),      (0,135,95),     (0,135,135),    (0,135,175),
  (0,135,215),    (0,135,255),    (0,175,0),      (0,175,95),
  (0,175,135),    (0,175,175),    (0,175,215),    (0,175,255),
  (0,215,0),      (0,215,95),     (0,215,135),    (0,215,175),
  (0,215,215),    (0,215,255),    (0,255,0),      (0,255,95),
  (0,255,135),    (0,255,175),    (0,255,215),    (0,255,255),
  (95,0,0),       (95,0,95),      (95,0,135),     (95,0,175),
  (95,0,215),     (95,0,255),     (95,95,0),      (95,95,95),
  (95,95,135),    (95,95,175),    (95,95,215),    (95,95,255),
  (95,135,0),     (95,135,95),    (95,135,135),   (95,135,175),
  (95,135,215),   (95,135,255),   (95,175,0),     (95,175,95),
  (95,175,135),   (95,175,175),   (95,175,215),   (95,175,255),
  (95,215,0),     (95,215,95),    (95,215,135),   (95,215,175),
  (95,215,215),   (95,215,255),   (95,255,0),     (95,255,95),
  (95,255,135),   (95,255,175),   (95,255,215),   (95,255,255),
  (135,0,0),      (135,0,95),     (135,0,135),    (135,0,175),
  (135,0,215),    (135,0,255),    (135,95,0),     (135,95,95),
  (135,95,135),   (135,95,175),   (135,95,215),   (135,95,255),
  (135,135,0),    (135,135,95),   (135,135,135),  (135,135,175),
  (135,135,215),  (135,135,255),  (135,175,0),    (135,175,95),
  (135,175,135),  (135,175,175),  (135,175,215),  (135,175,255),
  (135,215,0),    (135,215,95),   (135,215,135),  (135,215,175),
  (135,215,215),  (135,215,255),  (135,255,0),    (135,255,95),
  (135,255,135),  (135,255,175),  (135,255,215),  (135,255,255),
  (175,0,0),      (175,0,95),     (175,0,135),    (175,0,175),
  (175,0,215),    (175,0,255),    (175,95,0),     (175,95,95),
  (175,95,135),   (175,95,175),   (175,95,215),   (175,95,255),
  (175,135,0),    (175,135,95),   (175,135,135),  (175,135,175),
  (175,135,215),  (175,135,255),  (175,175,0),    (175,175,95),
  (175,175,135),  (175,175,175),  (175,175,215),  (175,175,255),
  (175,215,0),    (175,215,95),   (175,215,135),  (175,215,175),
  (175,215,215),  (175,215,255),  (175,255,0),    (175,255,95),
  (175,255,135),  (175,255,175),  (175,255,215),  (175,255,255),
  (215,0,0),      (215,0,95),     (215,0,135),    (215,0,175),
  (215,0,215),    (215,0,255),    (215,95,0),     (215,95,95),
  (215,95,135),   (215,95,175),   (215,95,215),   (215,95,255),
  (215,135,0),    (215,135,95),   (215,135,135),  (215,135,175),
  (215,135,215),  (215,135,255),  (215,175,0),    (215,175,95),
  (215,175,135),  (215,175,175),  (215,175,215),  (215,175,255),
  (215,215,0),    (215,215,95),   (215,215,135),  (215,215,175),
  (215,215,215),  (215,215,255),  (215,255,0),    (215,255,95),
  (215,255,135),  (215,255,175),  (215,255,215),  (215,255,255),
  (255,0,0),      (255,0,95),     (255,0,135),    (255,0,175),
  (255,0,215),    (255,0,255),    (255,95,0),     (255,95,95),
  (255,95,135),   (255,95,175),   (255,95,215),   (255,95,255),
  (255,135,0),    (255,135,95),   (255,135,135),  (255,135,175),
  (255,135,215),  (255,135,255),  (255,175,0),    (255,175,95),
  (255,175,135),  (255,175,175),  (255,175,215),  (255,175,255),
  (255,215,0),    (255,215,95),   (255,215,135),  (255,215,175),
  (255,215,215),  (255,215,255),  (255,255,0),    (255,255,95),
  (255,255,135),  (255,255,175),  (255,255,215),  (255,255,255),
  (8,8,8),        (18,18,18),     (28,28,28),     (38,38,38),
  (48,48,48),     (58,58,58),     (68,68,68),     (78,78,78),
  (88,88,88),     (98,98,98),     (108,108,108),  (118,118,118),
  (128,128,128),  (138,138,138),  (148,148,148),  (158,158,158),
  (168,168,168),  (178,178,178),  (188,188,188),  (198,198,198),
  (208,208,208),  (218,218,218),  (228,228,228),  (238,238,238)
)

ansi256_pal_map = dict((p[1], p[0]+16) for p in enumerate(ansi256_pal_vals))


ansi256_pal = Image.new('P', (1,1))
ansi256_pal.putpalette([n for s in ansi256_pal_vals for n in s])


def scale_image(img, char_width, block_size):
  img = img.convert('RGB')

  # Scale to specified width
  w, h = img.size

  new_w = char_width * block_size.w
  new_h = int(h / w * new_w)
  if block_size in ((2,2), (1,1)):  # Rectangular pixels
    new_h = new_h // 2;

  if new_h < 1:
    new_h = 1

  if block_size.h > 1: # Force an even number of lines
    new_h = (new_h + 1) & ~0x01

  return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def dither_image(img, palette):
  if palette is not None:
    return img.quantize(method=Image.Quantize.MEDIANCUT,
                        dither=Image.Dither.FLOYDSTEINBERG, palette=palette)
  else:
    return img.convert('1')



def median_cut(colors):
  '''Perform a single median cut on a color list'''
  channels = np.transpose(colors)
  #Find the channel with the greatest span
  chan_spans = [np.max(c) - np.min(c) for c in channels]
  cut_ix = chan_spans.index(max(chan_spans))

  med = int(np.median(channels[cut_ix]))
  below = 0
  for c in colors:
      if c[cut_ix] <= med:
        below += 1

  b = (np.ndarray(shape=(below, 3), dtype = np.int16),
       np.ndarray(shape=(len(colors) - below, 3), dtype = np.int16))
  blw_ix = 0
  abv_ix = 0
  for c in colors:
      if c[cut_ix] <= med:
        b[0][blw_ix] = c
        blw_ix += 1
      else:
        b[1][abv_ix] = c
        abv_ix += 1

  return b


def average_color(colors):
  return np.mean(colors, axis=0).astype(np.int16)


def color_dist(a, b):
  # Rough estimate with Euclidean distance
  # This is not rigorously correct but a more numerically involved
  # solution isn't a good fit for Python.

  # Skipping square root as it isn't needed for comparisons
  return (int(a[0])-int(b[0]))**2 + (int(a[1])-int(b[1]))**2 + (int(a[2])-int(b[2]))**2


def nearest_color(test_color, colors):
  d = [color_dist(test_color, c) for c in colors]
  return colors[d.index(min(d))]


def recolor_block(block, truecolor=False):
  '''Reduce a 2x2 block to two colors'''
  b2 = block.copy().reshape((1,4,3))[0]
  uniq, uniq_count = np.unique(b2, axis=0, return_counts=True)

  if uniq_count.size <= 2:  # No recoloring neded
    return

  if uniq_count.size == 3:
    # One color is duplicated on two pixels in the block.
    # Keep it and recolor the other two pixels.

    keep = uniq[uniq_count.argmax()]
    candidates = [c for c in uniq if not (c == keep).all()]

    # Choose the color most unlike the one we're keeping to maintain contrast
    remove = nearest_color(keep, candidates)
    selected = candidates[0] if not (remove == candidates[0]).all() else candidates[1]

    new_colors = (keep, selected)
    block[0,0] = nearest_color(block[0,0], new_colors)
    block[0,1] = nearest_color(block[0,1], new_colors)
    block[1,0] = nearest_color(block[1,0], new_colors)
    block[1,1] = nearest_color(block[1,1], new_colors)


  else: # Four unique colors
    # For palletized images we just copy the left column over as these blocks are
    # relatively uncommon and the resolution loss isn't impactful.
    # For 16M truecolor we perform a median cut to get two substitute colors. Otherwise
    # the horizontal resolution will be effectively reduced on all blocks with the copying
    # implementation as if 1x2 block size was selected.

    if not truecolor:
      # Copy the left column to the right
      block[0,1] = block[0,0]
      block[1,1] = block[1,0]

    else:
      # Perform one median cut to generate two buckets.
      # Then take their average to get the two new colors for this block.
      b = median_cut(uniq)
      if len(b[0]) == 0 or len(b[1]) == 0:
        # Cut left an empty bucket. This is uncommon so just use a single color
        b = (b[1], b[1]) if len(b[0]) == 0 else (b[0], b[0])


      new_colors = (average_color(b[0]), average_color(b[1]))
      #print('New:', new_colors)
      block[0,0] = nearest_color(block[0,0], new_colors)
      block[0,1] = nearest_color(block[0,1], new_colors)
      block[1,0] = nearest_color(block[1,0], new_colors)
      block[1,1] = nearest_color(block[1,1], new_colors)


def recolor(pix, truecolor=False):
  '''Convert 2x2 blocks to have only two colors'''
  h, w, _ = pix.shape

  for y in range(0, h-1, 2):
    for x in range(0, w-1, 2):
      block = pix[y:y+2, x:x+2] # Get 2x2 view into pix array
      recolor_block(block, truecolor)


def encode_ansi_16_color(fg, bg, pfg, pbg):
  '''Generate escape code for 16-color palette'''
  esc = ''

  # Generate color escape
  if fg != pfg:
    if bg != pbg and bg is not None:
      esc = '\033[{};{}m'.format(ansi_pal_map[fg], ansi_pal_map[bg]+10)
    else:
      esc = '\033[{}m'.format(ansi_pal_map[fg])

  elif bg != pbg and bg is not None:
    esc = '\033[{}m'.format(ansi_pal_map[bg]+10)

  return esc


def encode_ansi_256_color(fg, bg, pfg, pbg):
  '''Generate escape code for 256-color palette'''
  esc = ''

  # Generate color escape
  if fg != pfg:
    esc = '\033[38;5;{}m'.format(ansi256_pal_map[fg])

  if bg != pbg and bg is not None:
    esc += '\033[48;5;{}m'.format(ansi256_pal_map[bg])

  return esc


def encode_ansi_16M_color(fg, bg, pfg, pbg):
  '''Generate escape code for truecolor'''
  esc = ''

  # Generate color escape
  if fg != pfg:
    esc = '\033[38;2;{};{};{}m'.format(*fg)

  if bg != pbg and bg is not None:
    esc += '\033[48;2;{};{};{}m'.format(*bg)

  return esc


def encode_2x2_block(block, fg, chmap):
  # Get foreground bits
  tr = 1 if tuple(block[0,1]) == fg else 0
  bl = 1 if tuple(block[1,0]) == fg else 0
  br = 1 if tuple(block[1,1]) == fg else 0

  # Get Unicode block char
  ch = chmap[8 | (tr<<2) | (bl<<1) | br]
  return ch

def encode_1x2_block(block, fg, chmap):
  # Get foreground bits
  bl = 1 if tuple(block[1,0]) == fg else 0

  # Get Unicode block char
  ch = '█' if bl == 1 else '▀'
  return ch

def encode_1x1_block(block, fg, chmap):
  return '█'


def to_ansi_color(pix, encode_color, encode_char, chmap, block_size):
  '''Convert pixel data to encoded ANSI characters'''
  h, w, _ = pix.shape

  for y in range(0, h-1, block_size.h):
    pfg = None
    pbg = None

    for x in range(0, w-1, block_size.w):
      block = pix[y:y+block_size.h, x:x+block_size.w] # Get view into pix array

      # Get colors for this block
      fg = tuple(block[0,0])  # Top left is always foreground
      bg = None

      for p in (c for r in block for c in r):
        if tuple(p) != fg:
          bg = tuple(p)
          break

      print(encode_color(fg, bg, pfg, pbg) + encode_char(block, fg, chmap), end='')

      pfg = fg
      pbg = bg

    print('\033[0m')  # Clear colors at EOL


def to_cp437_color(pix, encode_char, block_size):
  '''Convert pixel data to encoded ANSI characters following CP437 rules'''
  h, w, _ = pix.shape

  for y in range(0, h-1, block_size.h):
    pfg = None
    pbg = None

    for x in range(0, w-1, block_size.w):
      block = pix[y:y+block_size.h, x:x+block_size.w] # Get view into pix array

      chmap = cp437_2x2

      # Get colors for this block
      fg = tuple(block[0,0])  # Top left is always foreground
      bg = None

      for p in (c for r in block for c in r):
        if tuple(p) != fg:
          bg = tuple(p)
          bgc = ansi_pal_map[bg]+10
          if bgc >= 90: # Can't have bright background, swap with foreground
            fg, bg = (bg, fg)
            chmap = cp437_2x2_inv

            bgc = ansi_pal_map[bg]+10
            if bgc >= 90: # Both are bright. Force background to dim
              bg = ansi_pal_rev_map[bgc - 60 - 10]
          break

      # FIXME: 16-color encoder doesn't use old style bright/bold code
      print(encode_ansi_16_color(fg, bg, pfg, pbg) + encode_char(block, fg, chmap), end='')

      pfg = fg
      pbg = bg

    print('\033[0m')  # Clear colors at EOL


def encode_2x2_block_bw(block, fg, chmap):
  tl = 1 if tuple(block[0,0]) == fg else 0
  tr = 1 if tuple(block[0,1]) == fg else 0
  bl = 1 if tuple(block[1,0]) == fg else 0
  br = 1 if tuple(block[1,1]) == fg else 0

  # Get Unicode block char
  ch = chmap[(tl<<3) | (tr<<2) | (bl<<1) | br]
  return ch

def encode_1x2_block_bw(block, fg, chmap):
  tl = 1 if tuple(block[0,0]) == fg else 0
  bl = 1 if tuple(block[1,0]) == fg else 0

  # Duplicate tl and bl bits to build index into 16-char map
  #   00 ->   0000
  #   01 -> ▄ 0011
  #   10 -> ▀ 1100
  #   11 -> █ 1111

  # Get Unicode block char
  ch = chmap[(tl<<3) | (tl<<2) | (bl<<1) | bl]
  return ch

def encode_1x1_block_bw(block, fg, chmap):
  return chmap[15] if tuple(block[0,0]) == fg else chmap[0]


def to_unicode_bw(pix, encode_char, chmap, block_size):
  '''Convert pixel data to black and white characters'''
  h, w, _ = pix.shape

  for y in range(0, h-1, block_size.h):
    for x in range(0, w-1, block_size.w):
      block = pix[y:y+block_size.h, x:x+block_size.w] # Get view into pix array
      print(encode_char(block, (255,255,255), chmap), end='')
    print()



def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('file', help='Image file')
  parser.add_argument('-c', '--colors', default='256', choices=['2', '16', '256', '16M'],
                      help='Set color depth')
  parser.add_argument('-w', '--width', type=int, default=-1, help='Width in chars')
  parser.add_argument('-b', '--block', default='2x2', choices=['1x1', '1x2', '2x2'], help='Block size')
  parser.add_argument('-g', '--gray', action='store_true', help='Grayscale')
  parser.add_argument('-i', '--invert', action='store_true', help='Invert image')
  parser.add_argument('--cp437', action='store_true', help='Restrict chars to CP437')
  parser.add_argument('-v', '--version', action='version', version="%(prog)s " + VERSION)
  args = parser.parse_args()

  # Process arguments
  args.colors = 2**24 if args.colors == '16M' else int(args.colors)

  if args.width < 1:
    args.width = shutil.get_terminal_size()[0] # Default to full terminal width

  block_size = BlockSize(*(int(d) for d in args.block.split('x')))

  # Select encoder functions
  if args.colors == 2:
    palette = None
    encode_color = None
  elif args.colors == 16:
    palette = ansi_pal
    encode_color = encode_ansi_16_color
  elif args.colors == 256:
    palette = ansi256_pal
    encode_color = encode_ansi_256_color
  else: # 16M colors
    palette = None
    encode_color = encode_ansi_16M_color

  if block_size.w > 1: # 2x2 block
    encode_char = encode_2x2_block if args.colors > 2 else encode_2x2_block_bw
  elif block_size.h > 1: # 1x2 block
    encode_char = encode_1x2_block if args.colors > 2 else encode_1x2_block_bw
  else: # 1x1 block
    encode_char = encode_1x1_block if args.colors > 2 else encode_1x1_block_bw


  # Filter image
  try:
    img = Image.open(args.file)
  except FileNotFoundError:
    print('File "{}" not found'.format(args.file))
    sys.exit(1)
  except PIL.UnidentifiedImageError:
    print('Unknown image format')
    sys.exit(1)

  img = scale_image(img, args.width, block_size)

  if args.gray:
    img = img.convert('L').convert('RGB')

  if args.invert:
    img = ImageOps.invert(img)

  if args.colors <= 256:
    img = dither_image(img, palette);
    #img.save('dither.gif')

  # Extract pixel data
  pix = np.asarray(img.convert('RGB')).copy()

  # Generate text output
  chmap = unicode_2x2 if args.cp437 == False else cp437_2x2

  if args.colors > 2:
    if block_size.w > 1: # 2x2 blocks must be reduced to two colors
      recolor(pix, args.colors > 256)

    if args.cp437 and args.colors == 16:  # Special rendering for traditional ANSI
      to_cp437_color(pix, encode_char, block_size)
    else: # Normal color rendering
      to_ansi_color(pix, encode_color, encode_char, chmap, block_size)

  else: # Black and white
    to_unicode_bw(pix, encode_char, chmap, block_size)

if __name__ == '__main__':
  main()

