"""Shared geographic bounds and verified distance bars for the audit figures."""
import math
def position(row):
    lat, lon = float(row["latitude"]), float(row["longitude"])
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"Invalid geographic position: {row['well_id']}")
    return lon, lat


def extent(rows, padding=.08):
    xs, ys = zip(*(position(row) for row in rows))
    dx, dy = max(xs)-min(xs), max(ys)-min(ys)
    return min(xs)-padding*dx, max(xs)+padding*dx, min(ys)-padding*dy, max(ys)+padding*dy


def inside(row, bounds):
    x, y = position(row)
    return bounds[0] <= x <= bounds[1] and bounds[2] <= y <= bounds[3]


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8*2*math.asin(math.sqrt(min(1,max(0,h))))


def scale_bar(ax, bounds, length):
    xmin, xmax, ymin, ymax = bounds
    lat = ymin+.075*(ymax-ymin)
    start = xmin+.07*(xmax-xmin)
    width = math.degrees(2*math.asin(math.sin(length/(2*6371008.8))/math.cos(math.radians(lat))))
    assert abs(distance((lat,start),(lat,start+width))-length) < .001
    tick = .012*(ymax-ymin)
    ax.plot([start,start+width],[lat,lat],color="#253345",linewidth=2.3,zorder=8)
    for x in (start,start+width):
        ax.plot([x,x],[lat-tick,lat+tick],color="#253345",linewidth=1.5,zorder=8)
    ax.text(start+width/2,lat+tick*2.2,f"{length//1000} km",ha="center",va="bottom",fontsize=10,
            color="#253345",bbox={"facecolor":"white","edgecolor":"none","alpha":.9},zorder=9)

