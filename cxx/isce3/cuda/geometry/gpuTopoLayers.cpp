#include "gpuTopoLayers.h"

#include <cuda_runtime.h>
#include <isce3/geometry/TopoLayers.h>
#include <isce3/cuda/except/Error.h>

namespace isce3 { namespace cuda { namespace geometry {
    gpuTopoLayers::gpuTopoLayers(const isce3::geometry::TopoLayers & layers) :
        _length(layers.length()), _width(layers.width()), _owner(true) {

        // Allocate memory
        _nbytes_double = _length * _width * sizeof(double);
        _nbytes_float = _length * _width * sizeof(float);
        checkCudaErrors(cudaMalloc((double **) &_x, _nbytes_double));
        checkCudaErrors(cudaMalloc((double **) &_y, _nbytes_double));
        checkCudaErrors(cudaMalloc((double **) &_z, _nbytes_double));
        checkCudaErrors(cudaMalloc((float **) &_inc, _nbytes_float));
        checkCudaErrors(cudaMalloc((float **) &_hdg, _nbytes_float));
        checkCudaErrors(cudaMalloc((float **) &_localInc, _nbytes_float));
        checkCudaErrors(cudaMalloc((float **) &_localPsi, _nbytes_float));
        checkCudaErrors(cudaMalloc((float **) &_sim, _nbytes_float));
        checkCudaErrors(cudaMalloc((double **) &_crossTrack, _nbytes_double));
    }

    // Destructor
    gpuTopoLayers::~gpuTopoLayers() {
        if (_owner) {
            checkCudaErrors(cudaFree(_x));
            checkCudaErrors(cudaFree(_y));
            checkCudaErrors(cudaFree(_z));
            checkCudaErrors(cudaFree(_inc));
            checkCudaErrors(cudaFree(_hdg));
            checkCudaErrors(cudaFree(_localInc));
            checkCudaErrors(cudaFree(_localPsi));
            checkCudaErrors(cudaFree(_sim));
            checkCudaErrors(cudaFree(_crossTrack));
        }
    }

    // Copy results to host TopoLayers
    void gpuTopoLayers::copyToHost(isce3::geometry::TopoLayers & layers) {
        if (layers.hasXRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.x()[0], _x, _nbytes_double,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasYRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.y()[0], _y, _nbytes_double,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasZRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.z()[0], _z, _nbytes_double,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasIncRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.inc()[0], _inc, _nbytes_float,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasHdgRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.hdg()[0], _hdg, _nbytes_float,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasLocalIncRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.localInc()[0], _localInc, _nbytes_float,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasLocalPsiRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.localPsi()[0], _localPsi, _nbytes_float,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasSimRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.sim()[0], _sim, _nbytes_float,
                            cudaMemcpyDeviceToHost));
        }
        if (layers.hasMaskRaster()) {
            checkCudaErrors(cudaMemcpy(&layers.crossTrack()[0], _crossTrack, _nbytes_double,
                            cudaMemcpyDeviceToHost));
        }
    }
} } }
