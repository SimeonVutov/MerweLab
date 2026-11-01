import {
  Cartesian3, ClassificationType, Color, ColorGeometryInstanceAttribute,
  GeometryInstance, GroundPrimitive, PerInstanceColorAppearance, PolygonGeometry, PolygonHierarchy,
} from 'cesium';

// A terrain classification overlay avoids coplanar mesh flicker and cutout gaps.
// The OBJ footprint is preserved; the display follows terrain rather than a second plane.
export async function loadWaterSurface(signal: AbortSignal): Promise<GroundPrimitive> {
  const response = await fetch('/web/surfaces/water-mask.geojson', { signal });
  const contentType = response.headers.get('content-type')?.split(';')[0]?.trim().toLowerCase();
  if (!response.ok) throw new Error(`Water footprint returned HTTP ${response.status}`);
  if (contentType !== 'application/json' && contentType !== 'application/geo+json') {
    throw new Error(`Water footprint returned ${contentType ?? 'no content type'} instead of GeoJSON. Restart the frontend server.`);
  }
  const mask: { geometry: { type: string; coordinates: number[][][][] } } = await response.json();
  const polygons = mask.geometry?.coordinates;
  if (mask.geometry?.type !== 'MultiPolygon' || !polygons?.length
    || !polygons.every((polygon) => polygon.length > 0 && polygon.every((ring) => ring.length >= 4
      && ring.every((point) => point.length === 2 && point.every(Number.isFinite))))) {
    throw new Error('Invalid water footprint');
  }
  const hierarchy = (ring: number[][]) => new PolygonHierarchy(Cartesian3.fromDegreesArray(ring.slice(0, -1).flat()));
  return new GroundPrimitive({
    geometryInstances: polygons.map(([outer, ...holes]) => new GeometryInstance({
      geometry: new PolygonGeometry({
        polygonHierarchy: new PolygonHierarchy(hierarchy(outer!).positions, holes.map(hierarchy)),
        vertexFormat: PerInstanceColorAppearance.VERTEX_FORMAT,
      }),
      attributes: { color: ColorGeometryInstanceAttribute.fromColor(Color.fromCssColorString('#71858c')) },
    })),
    appearance: new PerInstanceColorAppearance({ flat: true, translucent: false }),
    classificationType: ClassificationType.TERRAIN,
    show: false,
  });
}
