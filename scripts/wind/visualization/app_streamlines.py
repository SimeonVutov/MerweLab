import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy, numpy_to_vtkIdTypeArray
from vtkmodules.vtkCommonDataModel import vtkDataObject, vtkCellArray
from vtkmodules.vtkFiltersFlowPaths import vtkStreamTracer

from app_sampling import polydata, probe, to_cfd_rd
from coordinates import to_rd
import settings


def segments(points, speeds, valid, spacing=2):
    result = []
    starts = np.flatnonzero(valid & ~np.r_[False, valid[:-1]])
    ends = np.flatnonzero(valid & ~np.r_[valid[1:], False]) + 1
    for start, end in zip(starts, ends):
        if end - start < 2:
            continue
        keep = [start]
        for i in range(start + 1, end - 1):
            if np.linalg.norm(points[i] - points[keep[-1]]) >= spacing:
                keep.append(i)
        keep.append(end - 1)
        result.append({'points': points[keep].round(4).tolist(), 'speed': speeds[keep].round(5).tolist()})
    return result


def streamlines_3d(flow, ground, bounds):
    xyz = to_cfd_rd(np.array([[bounds[0], bounds[1], 0], [bounds[2], bounds[3], 0], [bounds[0], bounds[3], 0], [bounds[2], bounds[1], 0]]))
    seeds = np.array([(settings.SEED_X['overview'], y, z) for z in settings.SEED_HEIGHTS for y in np.linspace(xyz[:, 1].min(), xyz[:, 1].max(), 28)])
    valid = probe(flow, seeds)['vtkValidPointMask'].astype(bool)
    print(f'3D streamline seeds in air: {valid.sum()}/{len(seeds)}', flush=True)
    if not valid.any():
        raise ValueError('No 3D streamline seeds lie inside the saved flow')
    source = polydata(seeds[valid])
    vertices = vtkCellArray()
    vertices.SetCells(int(valid.sum()), numpy_to_vtkIdTypeArray(np.column_stack((np.ones(valid.sum(), dtype=np.int64), np.arange(valid.sum()))).ravel(), deep=True))
    source.SetVerts(vertices)
    flow.GetPointData().SetActiveVectors('U')
    tracer = vtkStreamTracer()
    tracer.SetInputData(flow)
    tracer.SetSourceData(source)
    tracer.SetInputArrayToProcess(0, 0, 0, vtkDataObject.FIELD_ASSOCIATION_POINTS, 'U')
    tracer.SetIntegrationDirectionToForward()
    tracer.SetIntegratorTypeToRungeKutta45()
    tracer.SetInterpolatorTypeToCellLocator()
    tracer.SetInitialIntegrationStep(0.3)
    tracer.SetMaximumNumberOfSteps(12000)
    tracer.SetMaximumPropagation(2200)
    tracer.SetComputeVorticity(False)
    tracer.Update()
    output = tracer.GetOutput()
    if not output.GetNumberOfLines():
        raise ValueError('No 3D streamlines were produced')
    points = to_rd(vtk_to_numpy(output.GetPoints().GetData()))
    speed = np.linalg.norm(vtk_to_numpy(output.GetPointData().GetArray('U')), axis=1)
    packed = vtk_to_numpy(output.GetLines().GetData())
    result, cursor = [], 0
    while cursor < len(packed):
        count = packed[cursor]
        indices = packed[cursor + 1:cursor + count + 1]
        p, s = points[indices], speed[indices]
        keep = (p[:, 0] >= bounds[0]) & (p[:, 0] <= bounds[2]) & (p[:, 1] >= bounds[1]) & (p[:, 1] <= bounds[3]) & (p[:, 2] <= 100) & np.isfinite(s)
        result.extend(segments(p, s, keep))
        cursor += count + 1
    if not result:
        raise ValueError('3D streamlines do not intersect the study area')
    return result


def streamlines_2d(velocity, valid, x, y, ground):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt

    u = np.ma.array(velocity[::-1, :, 0], mask=~valid[::-1])
    v = np.ma.array(velocity[::-1, :, 1], mask=~valid[::-1])
    figure, axes = plt.subplots()
    paths = axes.streamplot(x, y[::-1], u, v, density=1.8, minlength=0.05, maxlength=4).lines.get_segments()
    plt.close(figure)
    result = []
    for path in paths:
        if len(path) < 2:
            continue
        rd = np.column_stack((path, np.zeros(len(path))))
        cfd = to_cfd_rd(rd)
        cfd[:, 2] = 0
        heights = probe(ground, cfd)
        rd[:, 2] = heights['ground_z'] + 1.5
        col = np.clip(np.rint((path[:, 0] - x[0]) / (x[1] - x[0])).astype(int), 0, len(x) - 1)
        row = np.clip(np.rint((y[0] - path[:, 1]) / (y[0] - y[1])).astype(int), 0, len(y) - 1)
        speed = np.linalg.norm(velocity[row, col], axis=1)
        keep = heights['vtkValidPointMask'].astype(bool) & valid[row, col] & np.isfinite(speed)
        result.extend(segments(rd, speed, keep))
    if not result:
        raise ValueError('No 2D streamlines were produced')
    return result
