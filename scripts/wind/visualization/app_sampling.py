from pathlib import Path

import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy, numpy_to_vtkIdTypeArray
from vtkmodules.vtkCommonCore import vtkPoints, vtkSMPTools
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkFiltersCore import vtkAppendFilter, vtkCellDataToPointData, vtkCleanPolyData, vtkProbeFilter
from vtkmodules.vtkIOParallel import vtkPOpenFOAMReader

from coordinates import placement, to_rd
import settings


GROUPS = {'context_land', 'peninsula_ground', 'peninsula_paved', 'peninsula_green', 'existing_platform_rim', 'water'}


def check_memory(minimum_gib=3):
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
    if available < minimum_gib * 1024**3:
        raise MemoryError(f'Only {available / 1024**3:.1f} GiB available; postpone wind export until other work finishes')


def polydata(points):
    vertices = vtkPoints()
    vertices.SetData(numpy_to_vtk(np.ascontiguousarray(points), deep=True))
    data = vtkPolyData()
    data.SetPoints(vertices)
    return data


def probe(source, points):
    sampler = vtkProbeFilter()
    sampler.SetInputData(polydata(points))
    sampler.SetSourceData(source)
    sampler.SetComputeTolerance(False)
    sampler.SetTolerance(1e-7)
    sampler.Update()
    result = sampler.GetOutput().GetPointData()
    return {result.GetArrayName(i): vtk_to_numpy(result.GetArray(i)).copy() for i in range(result.GetNumberOfArrays())}


def ground_surface(scenario):
    path = settings.ROOT / f'analysis/wind/{scenario}/wind_240/constant/triSurface/terrain_hull.obj'
    points, faces = [], []
    group = ''
    for line in path.read_text().splitlines():
        words = line.split()
        if not words:
            continue
        if words[0] == 'v':
            points.append(list(map(float, words[1:4])))
        elif words[0] == 'g':
            group = ' '.join(words[1:])
        elif words[0] == 'f' and group in GROUPS:
            face = [int(word.split('/')[0]) - 1 for word in words[1:]]
            if len(face) != 3:
                raise ValueError('Expected triangulated CFD ground')
            faces.append(face)
    points, faces = np.asarray(points), np.asarray(faces)
    triangles = points[faces]
    keep = np.abs(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])[:, 2]) > 1e-10
    faces = faces[keep]
    data = polydata(points)
    cells = vtkCellArray()
    cells.SetCells(len(faces), numpy_to_vtkIdTypeArray(np.column_stack((np.full(len(faces), 3), faces)).ravel(), deep=True))
    data.SetPolys(cells)
    clean = vtkCleanPolyData()
    clean.SetInputData(data)
    clean.Update()
    ground = clean.GetOutput()
    z = vtk_to_numpy(ground.GetPoints().GetData())[:, 2].copy()
    values = numpy_to_vtk(z, deep=True)
    values.SetName('ground_z')
    ground.GetPointData().AddArray(values)
    flattened = vtk_to_numpy(ground.GetPoints().GetData())
    rd = to_rd(flattened.copy())
    flattened[:, 2] = 0
    ground.GetPoints().Modified()
    return ground, [np.floor(rd[:, 0].min()), np.floor(rd[:, 1].min()), np.ceil(rd[:, 0].max()), np.ceil(rd[:, 1].max())]


def to_cfd_rd(points):
    data = placement()
    fx, fy, _ = data['flow_unit_vector_RD']
    result = np.asarray(points) - data['RD_origin']
    result[:, :2] = result[:, :2] @ np.array([[fx, -fy], [fy, fx]])
    return result


def read_flow(scenario, iteration):
    check_memory(8)
    vtkSMPTools.Initialize(2)
    reader = vtkPOpenFOAMReader()
    reader.SetFileName(str(settings.ROOT / f'analysis/wind/{scenario}/wind_240/visualization.foam'))
    reader.SetCaseType(0)
    reader.SetCreateCellToPoint(0)
    reader.SetCacheMesh(0)
    reader.UpdateInformation()
    reader.DisableAllCellArrays()
    for field in ('U', 'k', 'p'):
        reader.SetCellArrayStatus(field, 1)
    reader.DisableAllPatchArrays()
    reader.SetPatchArrayStatus('internalMesh', 1)
    times = vtk_to_numpy(reader.GetTimeValues())
    if iteration not in times:
        raise ValueError(f'Missing saved iteration {iteration} for {scenario}')
    print(f'Reading {scenario}, iteration {iteration} (saved results only)...', flush=True)
    reader.UpdateTimeStep(iteration)
    blocks = reader.GetOutput()
    iterator = blocks.NewIterator()
    iterator.VisitOnlyLeavesOn()
    append = vtkAppendFilter()
    append.MergePointsOn()
    iterator.InitTraversal()
    while not iterator.IsDoneWithTraversal():
        block = iterator.GetCurrentDataObject()
        if block is not None and block.GetNumberOfCells():
            append.AddInputData(block)
        iterator.GoToNextItem()
    append.Update()
    check_memory()
    convert = vtkCellDataToPointData()
    convert.SetInputData(append.GetOutput())
    convert.PassCellDataOff()
    convert.Update()
    flow = convert.GetOutput()
    for field in ('U', 'k', 'p'):
        if flow.GetPointData().GetArray(field) is None:
            raise ValueError(f'Missing {field} field')
    print(f'Loaded {flow.GetNumberOfCells():,} cells; field sampling ready', flush=True)
    return flow
