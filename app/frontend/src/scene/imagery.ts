import {
  buildModuleUrl,
  Credit,
  ImageryLayer,
  Rectangle,
  TileMapServiceImageryProvider,
  UrlTemplateImageryProvider,
  WebMercatorTilingScheme,
} from 'cesium';

export function createGlobeImagery() {
  return ImageryLayer.fromProviderAsync(
    TileMapServiceImageryProvider.fromUrl(
      buildModuleUrl('Assets/Textures/NaturalEarthII'),
      { credit: 'Natural Earth' },
    ),
  );
}

export function createAerialImagery() {
  const provider = new UrlTemplateImageryProvider({
    url: 'https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_ortho25/EPSG:3857/{z}/{x}/{y}.jpeg',
    tilingScheme: new WebMercatorTilingScheme(),
    rectangle: Rectangle.fromDegrees(3.2, 50.7, 7.3, 53.7),
    maximumLevel: 19,
    hasAlphaChannel: false,
    enablePickFeatures: false,
    credit: new Credit(
      '<a href="https://www.pdok.nl/introductie/-/article/pdok-luchtfoto-rgb-open-" target="_blank" rel="noopener noreferrer">PDOK / Beeldmateriaal</a> · CC BY',
      true,
    ),
  });

  return new ImageryLayer(provider);
}
