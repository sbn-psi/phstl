#!/usr/bin/python

from math import sqrt
import sys
import argparse

import gdal
import stl

ap = argparse.ArgumentParser(description='Convert a GDAL raster (like a GeoTIFF heightmap) to an STL terrain surface.')
ap.add_argument('-x', action='store', default=0.0, type=float, help='Fit output x to extent (mm)')
ap.add_argument('-y', action='store', default=0.0, type=float, help='Fit output y to extent (mm)')
ap.add_argument('-z', action='store', default=1.0, type=float, help='Vertical scale factor')
ap.add_argument('-b', action='store', default=0.0, type=float, help='Base height')
ap.add_argument('-c', action='store_true', default=False, help='Clip z to minimum elevation')
ap.add_argument('RASTER', help='Input heightmap image')
ap.add_argument('STL', help='Output terrain mesh')
args = ap.parse_args()

#
#
#
def mapx(r, c):
	return transform[0] + (c * transform[1]) + (r * transform[2])

#
#
#
def mapy(r, c):
	return transform[3] + (c * transform[4]) + (r * transform[5])

# return normal vector of triangle surface
# t = (a, b, c) where a, b, and c are of form (x, y, z)
#
def norm(t):
	
	(ax, ay, az) = t[0]
	(bx, by, bz) = t[1]
	(cx, cy, cz) = t[2]
	
	# first edge
	e1x = ax - bx
	e1y = ay - by
	e1z = az - bz
	
	# second edge
	e2x = bx - cx
	e2y = by - cy
	e2z = bz - cz
	
	# cross product
	cpx = e1y * e2z - e1z * e2y
	cpy = e1z * e2x - e1x * e2z
	cpz = e1x * e2y - e1y * e2x
	
	# return cross product vector normalized to unit length
	mag = sqrt((cpx * cpx) + (cpy * cpy) + (cpz * cpz))
	return (cpx/mag, cpy/mag, cpz/mag)

#
#
#
def e2z(e):
	return (zscale * (float(e) - zmin)) + args.b

img = gdal.Open(args.RASTER)
cols = img.RasterXSize
rows = img.RasterYSize

transform = img.GetGeoTransform()
xyres = transform[1]
zscale = args.z

if args.x != 0.0 or args.y != 0.0:
	
	if args.x != 0.0 and args.y != 0.0:
		pixel_scale = min(args.x / (cols - 1), args.y / (rows - 1))
	elif args.x != 0.0:
		pixel_scale = args.x / (cols - 1)
	elif args.y != 0.0:
		pixel_scale = args.y / (rows - 1)
	
	zscale *= pixel_scale / xyres
	transform = (
			-pixel_scale * (cols - 1) / 2.0,
			pixel_scale,
			0,
			pixel_scale * (rows - 1) / 2.0,
			0,
			-pixel_scale
	)

band = img.GetRasterBand(1)

# min, max, mean, sd
# may use data min for z clipping
stats = band.GetStatistics(True, True)
if args.c == True:
	zmin = stats[0]
else:
	zmin = 0

# use for masking (omit pixels with this value)
nodata = band.GetNoDataValue()

data = band.ReadAsArray()

mesh = stl.Solid(name="Surface")

for col in range(cols - 1):
	for row in range(rows - 1):

		ax = mapx(row, col)
		ay = mapy(row, col)
		ae = data[row, col]
		az = e2z(ae)

		bx = mapx(row + 1, col)
		by = mapy(row + 1, col)
		be = data[row + 1, col]
		if be == nodata:
			continue
		bz = e2z(be)

		cx = mapx(row, col + 1)
		cy = mapy(row, col + 1)
		ce = data[row, col + 1]
		if ce == nodata:
			continue
		cz = e2z(ce)

		dx = mapx(row + 1, col + 1)
		dy = mapy(row + 1, col + 1)
		de = data[row + 1, col + 1]
		dz = e2z(de)

		t1 = ((ax, ay, az), (bx, by, bz), (cx, cy, cz))
		t2 = ((dx, dy, dz), (cx, cy, cz), (bx, by, bz))

		if ae != nodata:
			mesh.add_facet(norm(t1), t1)
		
		if de != nodata:
			mesh.add_facet(norm(t2), t2)


stl = open(args.STL, 'w')
mesh.write_binary(stl)
stl.close()

