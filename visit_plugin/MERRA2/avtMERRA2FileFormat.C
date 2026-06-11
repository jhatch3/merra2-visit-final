// Copyright (c) Lawrence Livermore National Security, LLC and other VisIt
// Project developers.  See the top-level LICENSE file for dates and other
// details.  No copyright assignment is required to contribute to VisIt.

// ****************************************************************************
//  avtMERRA2FileFormat.C
//
//  Implementation of the MERRA-2 database reader.  Opens the NASA NetCDF file,
//  builds a rectilinear grid whose vertical axis is pressure converted to a
//  pseudo-height, and hands variables back to VisIt one timestep at a time.
//
//  NOT yet compiled (no dev SDK on this binary install) -- see BUILD.md. The
//  VisIt helper signatures follow VisIt 3.x conventions and may need small
//  tweaks for your exact source build.
// ****************************************************************************

#include <avtMERRA2FileFormat.h>

#include <string>

#include <vtkFloatArray.h>
#include <vtkRectilinearGrid.h>

#include <avtDatabaseMetaData.h>

#include <InvalidVariableException.h>
#include <InvalidFilesException.h>

#include <netcdf.h>
#include <cmath>

using std::string;

const float avtMERRA2FileFormat::H_KM   = 7.5f;
const float avtMERRA2FileFormat::P0_HPA = 1000.0f;

// throw a VisIt exception on any NetCDF error
#define NC_CHECK(call)                                                        \
    do {                                                                      \
        int _e = (call);                                                      \
        if (_e != NC_NOERR)                                                   \
            EXCEPTION1(InvalidFilesException, nc_strerror(_e));               \
    } while (0)


// ****************************************************************************
//  Method: avtMERRA2FileFormat constructor
// ****************************************************************************
avtMERRA2FileFormat::avtMERRA2FileFormat(const char *filename)
    : avtMTSDFileFormat(&filename, 1)
{
    fname  = filename;
    ncid   = -1;
    opened = false;
    nTime = nLev = nLat = nLon = 0;
}

avtMERRA2FileFormat::~avtMERRA2FileFormat()
{
    FreeUpResources();
}


// ****************************************************************************
//  Method: avtMERRA2FileFormat::OpenFile
//
//  Open the NetCDF file once; read dimensions and the lon/lat/lev axes, and
//  convert pressure to pseudo-height.
// ****************************************************************************
void
avtMERRA2FileFormat::OpenFile(void)
{
    if (opened)
        return;

    NC_CHECK(nc_open(fname.c_str(), NC_NOWRITE, &ncid));

    int dT, dL, dA, dO;
    size_t sT, sL, sA, sO;
    NC_CHECK(nc_inq_dimid(ncid, "time", &dT));
    NC_CHECK(nc_inq_dimlen(ncid, dT, &sT));
    NC_CHECK(nc_inq_dimid(ncid, "lev",  &dL));
    NC_CHECK(nc_inq_dimlen(ncid, dL, &sL));
    NC_CHECK(nc_inq_dimid(ncid, "lat",  &dA));
    NC_CHECK(nc_inq_dimlen(ncid, dA, &sA));
    NC_CHECK(nc_inq_dimid(ncid, "lon",  &dO));
    NC_CHECK(nc_inq_dimlen(ncid, dO, &sO));
    nTime = (int)sT;  nLev = (int)sL;  nLat = (int)sA;  nLon = (int)sO;

    lon.resize(nLon);
    lat.resize(nLat);
    std::vector<float> lev(nLev);
    int vO, vA, vL;
    NC_CHECK(nc_inq_varid(ncid, "lon", &vO));
    NC_CHECK(nc_get_var_float(ncid, vO, &lon[0]));
    NC_CHECK(nc_inq_varid(ncid, "lat", &vA));
    NC_CHECK(nc_get_var_float(ncid, vA, &lat[0]));
    NC_CHECK(nc_inq_varid(ncid, "lev", &vL));
    NC_CHECK(nc_get_var_float(ncid, vL, &lev[0]));

    // pressure (hPa) -> pseudo-height (km): the heart of the old formatter
    zkm.resize(nLev);
    for (int k = 0; k < nLev; ++k)
        zkm[k] = H_KM * std::log(P0_HPA / lev[k]);

    const char *cand[] = { "T", "QV", "U", "V", "OMEGA", "RH", "H" };
    for (int i = 0; i < 7; ++i)
    {
        int vid;
        if (nc_inq_varid(ncid, cand[i], &vid) == NC_NOERR)
            scalarVars.push_back(cand[i]);
    }

    opened = true;
}


// ****************************************************************************
//  Method: avtMERRA2FileFormat::GetNTimesteps
// ****************************************************************************
int
avtMERRA2FileFormat::GetNTimesteps(void)
{
    OpenFile();
    return nTime;
}


// ****************************************************************************
//  Method: avtMERRA2FileFormat::FreeUpResources
// ****************************************************************************
void
avtMERRA2FileFormat::FreeUpResources(void)
{
    if (opened)
    {
        nc_close(ncid);
        opened = false;
    }
}


// ****************************************************************************
//  Method: avtMERRA2FileFormat::PopulateDatabaseMetaData
//
//  One rectilinear mesh ("atmosphere") plus the scalar fields on it.
// ****************************************************************************
void
avtMERRA2FileFormat::PopulateDatabaseMetaData(avtDatabaseMetaData *md, int)
{
    OpenFile();

    avtMeshType mt = AVT_RECTILINEAR_MESH;
    int nblocks = 1;            // must be 1 for MTSD
    int block_origin = 0;
    int spatial_dimension = 3;
    int topological_dimension = 3;
    AddMeshToMetaData(md, "atmosphere", mt, NULL, nblocks, block_origin,
                      spatial_dimension, topological_dimension);

    for (size_t i = 0; i < scalarVars.size(); ++i)
        AddScalarVarToMetaData(md, scalarVars[i], "atmosphere", AVT_NODECENT);
}


// ****************************************************************************
//  Method: avtMERRA2FileFormat::GetMesh
//
//  x = longitude, y = latitude, z = pseudo-height (km).
// ****************************************************************************
vtkDataSet *
avtMERRA2FileFormat::GetMesh(int timestate, const char *meshname)
{
    OpenFile();

    vtkRectilinearGrid *rgrid = vtkRectilinearGrid::New();
    rgrid->SetDimensions(nLon, nLat, nLev);

    vtkFloatArray *xc = vtkFloatArray::New();
    xc->SetNumberOfTuples(nLon);
    for (int i = 0; i < nLon; ++i) xc->SetTuple1(i, lon[i]);
    rgrid->SetXCoordinates(xc);
    xc->Delete();

    vtkFloatArray *yc = vtkFloatArray::New();
    yc->SetNumberOfTuples(nLat);
    for (int i = 0; i < nLat; ++i) yc->SetTuple1(i, lat[i]);
    rgrid->SetYCoordinates(yc);
    yc->Delete();

    vtkFloatArray *zc = vtkFloatArray::New();
    zc->SetNumberOfTuples(nLev);
    for (int i = 0; i < nLev; ++i) zc->SetTuple1(i, zkm[i]);
    rgrid->SetZCoordinates(zc);
    zc->Delete();

    return rgrid;
}


// ****************************************************************************
//  Method: avtMERRA2FileFormat::GetVar
//
//  NetCDF stores T(time,lev,lat,lon) row-major, so one timestep is lon-fastest
//  then lat then lev -- exactly VTK's point order (x fastest). Direct read.
// ****************************************************************************
vtkDataArray *
avtMERRA2FileFormat::GetVar(int timestate, const char *varname)
{
    OpenFile();

    int vid;
    if (nc_inq_varid(ncid, varname, &vid) != NC_NOERR)
        EXCEPTION1(InvalidVariableException, varname);

    const int npts = nLon * nLat * nLev;
    vtkFloatArray *arr = vtkFloatArray::New();
    arr->SetNumberOfTuples(npts);

    size_t start[4] = { (size_t)timestate, 0, 0, 0 };
    size_t count[4] = { 1, (size_t)nLev, (size_t)nLat, (size_t)nLon };

    int e = nc_get_vara_float(ncid, vid, start, count,
                              (float *)arr->GetVoidPointer(0));
    if (e != NC_NOERR)
    {
        arr->Delete();
        EXCEPTION1(InvalidFilesException, nc_strerror(e));
    }

    // mask MERRA-2 fill values (~1e15, below-ground/missing) so they don't
    // skew the data range -- same as the Python formatter did
    float *p = (float *)arr->GetVoidPointer(0);
    for (int i = 0; i < npts; ++i)
        if (p[i] >= 1.0e14f)
            p[i] = std::nanf("");

    return arr;
}


// ****************************************************************************
//  Method: avtMERRA2FileFormat::GetVectorVar
//
//  We only expose scalar fields, so this should never be called. Provided to
//  satisfy the interface.
// ****************************************************************************
vtkDataArray *
avtMERRA2FileFormat::GetVectorVar(int timestate, const char *varname)
{
    EXCEPTION1(InvalidVariableException, varname);
}
