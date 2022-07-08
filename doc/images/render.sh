#!/bin/sh
FN=`mktemp sphere-XXXX.png`
povray +A +W1600 +H900 sphere.pov +O$FN
convert $FN -resize 800x800 sphere.png
rm $FN
