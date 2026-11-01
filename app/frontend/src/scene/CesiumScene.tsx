import { useEffect, useRef, useState } from 'react';
import type { ImageryLayer, Viewer } from 'cesium';
import { createViewer } from './createViewer';
import { createAerialImagery, createGlobeImagery } from './imagery';
import { resetCamera } from './camera';
import styles from './CesiumScene.module.css';

interface CesiumSceneProps {
  scenarioLabel: string;
  imageryVisible: boolean;
  imageryOpacity: number;
}

export default function CesiumScene({ scenarioLabel, imageryVisible, imageryOpacity }: CesiumSceneProps) {
  const container = useRef<HTMLDivElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const imagery = useRef<ImageryLayer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imageryError, setImageryError] = useState<string | null>(null);

  useEffect(() => {
    if (!container.current) return;
    let instance: Viewer;
    try {
      instance = createViewer(container.current);
    } catch (cause) {
      console.error('Cesium initialization failed', cause);
      setError('The 3D view could not start. Check that WebGL is enabled in your browser.');
      return;
    }

    viewer.current = instance;
    setError(null);
    setImageryError(null);
    const base = createGlobeImagery();
    const aerial = createAerialImagery();
    const removeBaseError = base.errorEvent.addEventListener(() => {
      setImageryError('Overview imagery could not load.');
    });
    const removeAerialError = aerial.imageryProvider.errorEvent.addEventListener(() => {
      setImageryError('Some aerial imagery could not load. Check your connection to PDOK.');
    });
    const removeRenderError = instance.scene.renderError.addEventListener(() => {
      setError('The 3D view stopped rendering. Reload the page to try again.');
    });
    instance.imageryLayers.add(base);
    instance.imageryLayers.add(aerial);
    imagery.current = aerial;
    const resizeObserver = new ResizeObserver(() => {
      instance.resize();
      instance.scene.requestRender();
    });
    resizeObserver.observe(container.current);

    return () => {
      resizeObserver.disconnect();
      removeBaseError();
      removeAerialError();
      removeRenderError();
      imagery.current = null;
      viewer.current = null;
      instance.destroy();
    };
  }, []);

  useEffect(() => {
    if (!viewer.current || !imagery.current) return;
    imagery.current.show = imageryVisible;
    imagery.current.alpha = imageryOpacity;
    viewer.current.scene.requestRender();
  }, [imageryVisible, imageryOpacity]);

  return (
    <>
      <div ref={container} className={styles.canvas} />
      <div className={styles.toolbar}>
        <button disabled={error !== null} onClick={() => viewer.current && resetCamera(viewer.current)}>Reset view</button>
      </div>
      <div className={styles.location}>Merwehaven · {scenarioLabel}</div>
      {imageryError && imageryVisible && !error && <p className={styles.message} role="status">{imageryError}</p>}
      {error && <p className={styles.message} role="alert">{error}</p>}
    </>
  );
}
