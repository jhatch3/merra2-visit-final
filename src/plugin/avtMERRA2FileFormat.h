// Copyright (c) Lawrence Livermore National Security, LLC and other VisIt
// Project developers.  See the top-level LICENSE file for dates and other
// details.  No copyright assignment is required to contribute to VisIt.

// ****************************************************************************
//  avtMERRA2FileFormat.h
//
//  Reads NASA MERRA-2 3D pressure-level files (inst3_3d_asm_Np, NetCDF-4)
//  directly into VisIt. This is the Python formatter (build_merra_series.py)
//  reimplemented as a native plugin: the pressure -> pseudo-height conversion
//  lives in GetMesh(), so VisIt opens the raw NASA .nc4 with no conversion step.
//
//  Generated skeleton from xml2plugin, then implemented. NOT yet compiled --
//  this binary VisIt install ships no dev SDK (see BUILD.md).
// ****************************************************************************

#ifndef AVT_MERRA2_FILE_FORMAT_H
#define AVT_MERRA2_FILE_FORMAT_H

#include <avtMTSDFileFormat.h>

#include <string>
#include <vector>


// ****************************************************************************
//  Class: avtMERRA2FileFormat
//
//  Purpose:
//      Reads one MERRA-2 .nc4 file (8 timesteps, single domain -> MTSD).
// ****************************************************************************

class avtMERRA2FileFormat : public avtMTSDFileFormat
{
  public:
                       avtMERRA2FileFormat(const char *);
    virtual           ~avtMERRA2FileFormat();

    virtual int            GetNTimesteps(void);

    virtual const char    *GetType(void)   { return "MERRA2"; }
    virtual void           FreeUpResources(void);

    virtual vtkDataSet    *GetMesh(int, const char *);
    virtual vtkDataArray  *GetVar(int, const char *);
    virtual vtkDataArray  *GetVectorVar(int, const char *);

  protected:
    // pressure (hPa) -> pseudo-height (km): z = H_KM * ln(P0_HPA / p)
    static const float       H_KM;        // scale height, 7.5 km
    static const float       P0_HPA;      // reference pressure, 1000 hPa

    std::string              fname;       // path to the .nc4 file
    int                      ncid;        // NetCDF file id
    bool                     opened;

    int                      nTime, nLev, nLat, nLon;
    std::vector<float>       lon, lat, zkm;   // axis coordinates
    std::vector<std::string> scalarVars;      // T, QV, U, V, ...

    void                     OpenFile(void);
    virtual void             PopulateDatabaseMetaData(avtDatabaseMetaData *, int);
};


#endif
