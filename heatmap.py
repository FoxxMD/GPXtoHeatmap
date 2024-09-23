import gpxpy
import click
import os
from configparser import ConfigParser
from decimal import *
import traceback

parser = ConfigParser()
parser.read('config.ini')
API_KEY = parser.get('GOOGLE', 'API_KEY')
INITIAL_LATITUDE = parser.get('MAP', 'LATITUDE')
INITIAL_LONGITUDE = parser.get('MAP', 'LONGITUDE')
INITIAL_ZOOM = parser.get('MAP', 'ZOOM')
getcontext().prec = 12

@click.command()
@click.option("--output", default="map", help="Specify the name of the output file. Defaults to `map`")
@click.option("--input", default="gpx", help="Specify an input folder. Defaults to `gpx`")
@click.option("--filter", default=None, help="Specify a filter type. Defaults to no filter", type=click.Choice(['running', 'cycling', 'walking']))
@click.option("--accuracy", default=4, help="Decimals places of lat/long to use Defaults to `5`")
@click.option("--average/--no-average", default=True, help="Average points below accuracy or use lat/long grouping?")
def main(output, input, filter,accuracy,average):
    points = load_points(input, filter, accuracy, average)
    generate_html(points, output)

def load_points(folder, filter,accuracy, average):
    """Loads all gpx files into a list of points"""
    coordMap = {}
    coords = []

    # https://gis.stackexchange.com/a/8674/121567
    PLACES = Decimal(10) ** (-1 * accuracy)
    UNDER_PLACES = Decimal(10) ** (-1 * accuracy)

    print (f"Loading files with type {filter}...") #Loads files with progressbar
    with click.progressbar(os.listdir(folder)) as bar:
        for filename in bar:
            if (filename.lower().endswith(".gpx")):
                #Verify file is a gpx file
                gpx_file = open(os.path.join(folder, filename))
                gpx = gpxpy.parse(gpx_file)
                for track in gpx.tracks:
                    if not filter or filter==track.type:
                        for segment in track.segments:
                            for point in segment.points:
                                try:
                                    lat = Decimal(point.latitude)
                                    long = Decimal(point.longitude)
                                    latgroup = lat.quantize(PLACES)
                                    longgroup = long.quantize(PLACES)
                                    k = ''.join([str(latgroup), str(longgroup)])
                                    if k in coordMap:
                                        coordMap[k]["count"] += 1
                                        if average:
                                            coordMap[k]["points"].append([lat,long])
                                    else:
                                        coordMap[k] = {"points": [], "count": 1}
                                        if average:
                                            coordMap[k]["points"].append([lat,long])
                                        else:
                                            coordMap[k]["points"].append([latgroup,longgroup])
                                except Exception:
                                    print("Failed coordinate load but continuning")
                                    print(traceback.format_exc())
                                #coords.append([Decimal(point.latitude).quantize(PLACES), Decimal(point.longitude).quantize(PLACES)])

    for key,value in coordMap.items():
        if average:
            latTotal = Decimal(0)
            longTotal = Decimal(0)
            for lat,long in value["points"]:
                latTotal = latTotal + lat
                longTotal = longTotal + long
            
            latavg = Decimal(latTotal / len(value["points"])).quantize(UNDER_PLACES)
            longavg = Decimal(longTotal / len(value["points"])).quantize(UNDER_PLACES)
            coords.append([[latavg, longavg], value["count"]])
        else:
            coords.append([value["points"][0], value["count"]])
    return (coords)

def get_outline():
    """Reads in the html outline file"""
    with open('map-outline.txt', 'r') as file:
        outline = file.read()
    return outline

def generate_html(points, file_out):
    """Generates a new html file with points"""
    if not os.path.exists('output'):
        os.mkdir('output')
    f = open(f"output/{file_out}.html", "w")
    outline = get_outline()
    #google_points = ",\n".join([f"new google.maps.LatLng({point[0]}, {point[1]})" for point in points])
    google_points = ",\n".join([f"{{location: new google.maps.LatLng({point[0][0]}, {point[0][1]}), weight: {point[1]}}}" for point in points])
    updated_content = outline.replace("LIST_OF_POINTS", google_points).replace("API_KEY", API_KEY).replace("INIT_LATITUDE", INITIAL_LATITUDE).replace("INIT_LONGITUDE", INITIAL_LONGITUDE).replace("INIT_ZOOM", INITIAL_ZOOM)
    f.write(updated_content)
    f.close()


if __name__ == '__main__':
    main()
