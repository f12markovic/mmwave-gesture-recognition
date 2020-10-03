/**
 *   @file  dss_data_path.h
 *
 *   @brief
 *      This is the data path processing header.
 *
 *  \par
 *  NOTE:
 *      (C) Copyright 2016 Texas Instruments, Inc.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *    Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 *    Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the
 *    distribution.
 *
 *    Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 *  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 *  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 *  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 *  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 *  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
#ifndef DSS_DATA_PATH_H
#define DSS_DATA_PATH_H

#include <ti/sysbios/knl/Semaphore.h>

#include <ti/common/sys_common.h>
#include <ti/common/mmwave_error.h>
#include <ti/demo/io_interface/mmw_config.h>
#include <ti/drivers/adcbuf/ADCBuf.h>
#include <ti/drivers/edma/edma.h>
#include <ti/demo/io_interface/detected_obj.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BYTES_PER_SAMP_1D (2*sizeof(int16_t))  /*16 bit real, 16 bit imaginary => 4 bytes */
#define BYTES_PER_SAMP_2D (2*sizeof(int32_t))  /*32 bit real, 32 bit imaginary => 8 bytes */
#define BYTES_PER_SAMP_DET sizeof(uint16_t) /*pre-detection matrix is 16 bit unsigned =>2 bytes*/

//DETECTION (CFAR-CA) related parameters
#define MMW_MAX_OBJ_OUT 100
#define MAX_DET_OBJECTS_RAW 2048 /* same as xwr14xx, should not exceed 65536 */
#define DET_THRESH_MULT 25
#define DET_THRESH_SHIFT 5 //DET_THRESH_MULT and DET_THRESH_SHIFT together define the CFAR-CA threshold
#define DET_GUARD_LEN 4 // this is the one sided guard lenght
#define DET_NOISE_LEN 16 //this is the one sided noise length

#define PI_ 3.1415926535897
#define ONE_Q15 (1 << 15)
#define ONE_Q19 (1 << 19)
#define ONE_Q8 (1 << 8)

/*!< Peak grouping scheme of CFAR detected objects based on peaks of neighboring cells taken from detection matrix */
#define MMW_PEAK_GROUPING_DET_MATRIX_BASED 1
/*!< Peak grouping scheme of CFAR detected objects based only on peaks of neighboring cells that are already detected by CFAR */
#define MMW_PEAK_GROUPING_CFAR_PEAK_BASED  2

/*!< cumulative average of left+right */
#define MMW_NOISE_AVG_MODE_CFAR_CA       ((uint8_t)0U)
/*!< cumulative average of the side (left or right) that is greater */
#define MMW_NOISE_AVG_MODE_CFAR_CAGO     ((uint8_t)1U)
/*!< cumulative average of the side (left or right) that is smaller */
#define MMW_NOISE_AVG_MODE_CFAR_CASO     ((uint8_t)2U)

/* To enable negative frequency slope support, uncomment the following definition.
 * Note that this is experimental and not tested option */
/* #define MMW_ENABLE_NEGATIVE_FREQ_SLOPE */

/* If the the following EDMA defines are commented out, the EDMA transfer completion is
   is implemented using polling apporach, Otherwise, if these defines are defined,
   the EDMA transfers are implemented using blocking approach, (data path task
   pending on semaphore, waiting for the transfer completion event, posted by
   EDMA transfer completion intedrupt. In these cases since the EDMA transfers
   are faster than DSP processing, polling approach is more appropriate. */
//#define EDMA_1D_INPUT_BLOCKING
//#define EDMA_1D_OUTPUT_BLOCKING
//#define EDMA_2D_INPUT_BLOCKING
//#define EDMA_2D_OUTPUT_BLOCKING
//#define EDMA_MATRIX2_INPUT_BLOCKING
//#define EDMA_3D_INPUT_BLOCKING

/*! @brief DSP cycle profiling structure to accumulate different
    processing times in chirp and frame processing periods */
typedef struct cycleLog_t_ {
    uint32_t interChirpProcessingTime; /*!< @brief total processing time during all chirps in a frame excluding EDMA waiting time*/
    uint32_t interChirpWaitTime; /*!< @brief total wait time for EDMA data transfer during all chirps in a frame*/
    uint32_t interFrameProcessingTime; /*!< @brief total processing time for 2D and 3D excluding EDMA waiting time*/
    uint32_t interFrameWaitTime; /*!< @brief total wait time for 2D and 3D EDMA data transfer */
} cycleLog_t;



/*!
 *  @brief    Parameters of CFAR detected object during the first round of
 *  CFAR detections
 *
 */
typedef struct MmwDemo_objRaw
{
    uint16_t   rangeIdx;     /*!< @brief Range index */
    uint16_t   dopplerIdx;   /*!< @brief Dopler index */
    uint16_t   peakVal;      /*!< @brief Peak value */
} MmwDemo_objRaw_t;

/*!
 *  @brief    Active Doppler lines, lines (bins) on which the
 *            CFAR detector detected objects during the detections in
 *            Doppler direction
 *
 */
typedef struct MmwDemo_1D_DopplerLines
{
    uint32_t   *dopplerLineMask;      /*!< @brief Doppler line bit mask of active
                                   (CFAR detected) Doppler bins in the first
                                   round of CFAR detections in DOppler direction.
                                   The LSB bit of the first word corresponds to
                                   Doppler bin zero of the range/Doppler
                                   detection matrix*/
    uint16_t   currentIndex;     /*!< @brief starting index for the search
                                   for next active Doppler line */
    uint16_t    dopplerLineMaskLen;   /*!< @brief size of dopplerLineMask array, (number of
                                    32_bit words, for example for Doppler FFT
                                    size of 64 this length is equal to 2)*/
} MmwDemo_1D_DopplerLines_t;

/*!
 *  @brief Timing information
 */
typedef struct MmwDemo_timingInfo
{
    /*! @brief number of processor cycles between frames excluding
           processing time to transmit output on UART and excluding
           sub-frame switching time in case of advanced frame */
    uint32_t interFrameProcCycles;

    /*! @brief sub-frame switching cycles in case of advanced frame */
    uint32_t subFrameSwitchingCycles;

    /*! @brief time to transmit out detection information (in DSP cycles)
           */
    uint32_t transmitOutputCycles;

    /*! @brief Chirp processing end time */
    uint32_t chirpProcessingEndTime;

    /*! @brief Chirp processing end margin in number of cycles before due time
     * to start processing next chirp, minimum value*/
    uint32_t chirpProcessingEndMarginMin;

    /*! @brief Chirp processing end margin in number of cycles before due time
     * to start processing next chirp, maximum value*/
    uint32_t chirpProcessingEndMarginMax;

    /*! @brief Inter frame processing end time */
    uint32_t interFrameProcessingEndTime;

    /*! @brief Inter frame processing end margin in number of cycles before
     * due time to start processing first chirp of the next frame */
    uint32_t interFrameProcessingEndMargin;

    /*! @brief CPU Load during active frame period - i.e. chirping */
    uint32_t activeFrameCPULoad;

    /*! @brief CPU Load during inter frame period - i.e. after chirps
     *  are done and before next frame starts */
    uint32_t interFrameCPULoad;

} MmwDemo_timingInfo_t;

/**
 * @brief
 *  Millimeter Wave Demo Data Path Context.
 *
 * @details
 *  The structure is used to hold common context among data path objects.
 */
typedef struct MmwDemo_DSS_dataPathContext_t_
{
    /*! @brief   ADCBUF handle. */
    ADCBuf_Handle adcbufHandle;

    /*! @brief   Handle of the EDMA driver. */
    EDMA_Handle edmaHandle[EDMA_NUM_CC];

#if 0 //presently we only assert when we hit error, not store into these globals
      //because user can still examine in CCS the locals to find which instance (from handle)
      //and what error

    /*! @brief   EDMA error Information when there are errors like missing events */
    EDMA_errorInfo_t  EDMA_errorInfo[EDMA_NUM_CC];

    /*! @brief EDMA transfer controller error information. */
    EDMA_transferControllerErrorInfo_t EDMA_transferControllerErrorInfo[EDMA_NUM_CC];
#endif

#ifdef EDMA_1D_INPUT_BLOCKING
    /*! @brief Semaphore handle for 1D EDMA completion. */
    Semaphore_Handle EDMA_1D_InputDone_semHandle[2];
#endif

#ifdef EDMA_1D_OUTPUT_BLOCKING
    /*! @brief Semaphore handle for 1D EDMA completion. */
    Semaphore_Handle EDMA_1D_OutputDone_semHandle[2];
#endif

#ifdef EDMA_2D_INPUT_BLOCKING
    /*! @brief Semaphore handle for 2D EDMA completion. */
    Semaphore_Handle EDMA_2D_InputDone_semHandle[2];
#endif

#ifdef EDMA_2D_OUTPUT_BLOCKING
    /*! @brief Semaphore handle for Detection Matrix completion. */
    Semaphore_Handle EDMA_DetMatrix_semHandle;
#endif

#ifdef EDMA_MATRIX2_INPUT_BLOCKING
    /*! @brief Semaphore handle for Detection Matrix2 completion. */
    Semaphore_Handle EDMA_DetMatrix2_semHandle;
#endif

#ifdef EDMA_3D_INPUT_BLOCKING
    /*! @brief Semaphore handle for 3D EDMA completion. */
    Semaphore_Handle EDMA_3D_InputDone_semHandle[2];
#endif

    /*! @brief  Used for checking that chirp processing finshed on time */
    int8_t chirpProcToken;

    /*! @brief  Used for checking that inter frame processing finshed on time */
    int8_t interFrameProcToken;

} MmwDemo_DSS_dataPathContext_t;

/**
 * @brief
 *  Millimeter Wave Demo Data Path CQ configuration.
 *
 * @details
 *  The structure is used to hold all the relevant information for
 *  the data path CQ.
 */
typedef struct MmwDemo_DSS_DataPathCQConfig_t
{
    /*! @brief Pointer to the CQ RX Saturation monitor configuration */
    rlRxSatMonConf_t        *rxSatMonCfg;

    /*! @brief Pointer to the CQ Signal and image band monitor configuration */
    rlSigImgMonConf_t       *sigImgMonCfg;

    /*! @brief Pointer to the CQ Signal and image band monitor configuration */
    MmwDemo_AnaMonitorCfg   *anaMonCfg;

    /*! @brief CQ signal & image band monitor buffer physical address */
    uint32_t                sigImgMonAddr;

    /*! @brief CQ RX Saturation monitor buffer physical address */
    uint32_t                satMonAddr;

    /*! @brief CQ signal & image band monitor data size per chirp */
    uint32_t                sigImgMonDataSizePerChirp;

    /*! @brief CQ RX Saturation monitor data size per chirp */
    uint32_t                satMonDataSizePerChirp;

    /*! @brief CQ signal & image band monitor buffer size */
    uint32_t                sigImgMonTotalSize;

    /*! @brief CQ RX Saturation monitor buffer size */
    uint32_t                satMonTotalSize;

    /*! @brief CQ RX signal & image band monitor EDMA complete counter */
    uint32_t                sigImgEdmaCnt;

    /*! @brief CQ RX signal & image band monitor EDMA error counter */
    uint32_t                sigImgErrCnt;

    /*! @brief CQ RX Saturation monitor EDMA complete counter */
    uint32_t                rxSatEdmaCnt;

    /*! @brief CQ RX Saturation monitor EDMA error counter */
    uint32_t                rxSatErrCnt;

    /*! @brief CQ RX Saturation monitor data */
    void*                   rxSatData;

    /*! @brief CQ signal & image band monitor data */
    void*                   sigImgData;
}MmwDemo_DSS_DataPathCQ;

/**
 * @brief
 *  Millimeter Wave Demo Data Path Information.
 *
 * @details
 *  The structure is used to hold all the relevant information for
 *  the data path.
 */
typedef struct MmwDemo_DSS_DataPathObj_t
{
    /*! @brief Pointer to mmw demo configuration */
    MmwDemo_Cfg *cfg;
    
    /*! @brief Pointer to common context across data path objects */
    MmwDemo_DSS_dataPathContext_t *context;

    /*! @brief Pointer to cli config */
    MmwDemo_CliCfg_t *cliCfg;

    /*! @brief Pointer to cli config common to all subframes*/
    MmwDemo_CliCommonCfg_t *cliCommonCfg;

    /*! @brief   Number of receive channels */
    uint8_t numRxAntennas;

    /*! @brief pointer to ADC buffer */
    cmplx16ReIm_t *ADCdataBuf;

    /*! @brief twiddle table for 1D FFT */
    cmplx16ReIm_t *twiddle16x16_1D;

    /*! @brief window coefficients for 1D FFT */
    int16_t *window1D;

    /*! @brief ADCBUF input samples in L2 scratch memory */
    cmplx16ReIm_t *adcDataIn;

    /*! @brief 1D FFT output */
    cmplx16ReIm_t *fftOut1D;

    /*! @brief twiddle table for 2D FFT */
    cmplx32ReIm_t *twiddle32x32_2D;

    /*! @brief window coefficients for 2D FFT */
    int32_t *window2D;

    /*! @brief ping pong buffer for 2D from radar Cube */
    cmplx16ReIm_t *dstPingPong;

    /*! @brief window output for 2D FFT */
    cmplx32ReIm_t *windowingBuf2D;

    /*! @brief 2D FFT output */
    cmplx32ReIm_t *fftOut2D;

    /*! @brief log2 absolute computation output buffer */
    uint16_t *log2Abs;

    /*! @brief accumulated sum of log2 absolute over the antennae */
    uint16_t *sumAbs;

    /*! @brief input buffer for CFAR processing from the detection matrix */
    uint16_t *sumAbsRange;

    /*! @brief CFAR output objects index buffer */
    uint16_t *cfarDetObjIndexBuf;

    /*! @brief input for Azimuth FFT */
    cmplx32ReIm_t *azimuthIn;

    /*! @brief output of Azimuth FFT */
    cmplx32ReIm_t *azimuthOut;

    /*! @brief output of Azimuth FFT magnitude squared */
    float   *azimuthMagSqr;

    /*! @brief twiddle factors table for Azimuth FFT */
    cmplx32ReIm_t *azimuthTwiddle32x32;

    /*! @brief Pointer to single point DFT coefficients used for Azimuth processing */
    cmplx16ImRe_t *azimuthModCoefs;

    /*! @brief Pointer to DC range signature compensation buffer */
    cmplx32ImRe_t *dcRangeSigMean;

    /*! @brief DC range signature calibration counter */
    uint16_t dcRangeSigCalibCntr;

    /*! @brief log2 of number of averaged chirps */
    uint8_t log2NumAvgChirps;

    /*! @brief Half bin needed for doppler correction as part of Azimuth processing */
    cmplx16ImRe_t azimuthModCoefsHalfBin;

    /*! @brief Pointer to Radar Cube memory in L3 RAM */
    cmplx16ReIm_t *radarCube;

    /*! @brief Pointer to range/Doppler log2 magnitude detection matrix in L3 RAM */
    uint16_t *detMatrix;

    /*! @brief Pointer to 2D FFT array in range direction, at doppler index 0,
     * for static azimuth heat map */
    cmplx16ImRe_t *azimuthStaticHeatMap;

    /*! @brief valid Profile index */
    uint8_t validProfileIdx;

    /*! @brief number of transmit antennas */
    uint8_t numTxAntennas;

    /*! @brief number of virtual antennas */
    uint8_t numVirtualAntennas;

    /*! @brief number of virtual azimuth antennas */
    uint8_t numVirtualAntAzim;

    /*! @brief number of virtual elevation antennas */
    uint8_t numVirtualAntElev;

    /*! @brief number of ADC samples */
    uint16_t numAdcSamples;

    /*! @brief number of range bins */
    uint16_t numRangeBins;

    /*! @brief number of chirps per frame */
    uint16_t numChirpsPerFrame;

    /*! @brief number of angle bins */
    uint16_t numAngleBins;

    /*! @brief number of doppler bins */
    uint16_t numDopplerBins;

    /*! @brief number of doppler bins */
    uint8_t log2NumDopplerBins;

    /*! @brief range resolution in meters */
    float rangeResolution;

    /*! @brief Q format of the output x/y/z coordinates */
    uint8_t xyzOutputQFormat;

    /*! @brief Number of detected objects */
    uint16_t numDetObj;

    /*! @brief Number of detected objects */
    uint16_t numDetObjRaw;

    /*! @brief Detected Doppler lines */
	MmwDemo_1D_DopplerLines_t detDopplerLines;

    /*! @brief Detected objects after second pass in Range direction */
    MmwDemo_detectedObj *detObj2D;

    /*! @brief Detected objects before peak grouping */
    MmwDemo_objRaw_t *detObj2DRaw;

    /*! @brief Detected objects azimuth index for debugging */
    uint8_t *detObj2dAzimIdx;

    /*! @brief Timing information */
    MmwDemo_timingInfo_t timingInfo;

    /*! @brief chirp counter modulo number of chirps per frame */
    uint16_t chirpCount;

    /*! @brief chirp counter modulo number of tx antennas */
    uint8_t txAntennaCount;

    /*! @brief chirp counter modulo number of Doppler bins */
    uint16_t dopplerBinCount;

    /*! @brief  DSP cycles for chirp and interframe processing and pending
     *          on EDMA data transferes*/
    cycleLog_t cycleLog;

    /*! @brief ADCBUF will generate chirp interrupt event every this many chirps */
    uint16_t   numChirpsPerChirpEvent;

    /*! @brief number of bytes per ADC sample in ADC buffer  */
    uint8_t    numBytePerSample;

    /*! @brief Rx channel gain/phase offset compensation coefficients */
    MmwDemo_compRxChannelBiasCfg_t compRxChanCfg;

    /*! @brief subframe index for this obj */
    uint8_t subFrameIndx;

    /*! @brief Rx channel Chirp Quality config & data */
    MmwDemo_DSS_DataPathCQ          datapathCQ;
} MmwDemo_DSS_DataPathObj;

/**
 *  @b Description
 *  @n
 *   Initializes data path object with supplied context and cli Config.
 *   The context and cli config point to permanent storage outside of data path object
 *   that data path object can refer to anytime during the lifetime of data path object.
 *   Data path default values that are not required to come through CLI commands are
 *   set in this function.
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_dataPathObjInit(MmwDemo_DSS_DataPathObj *obj,
                             MmwDemo_DSS_dataPathContext_t *context,
                             MmwDemo_CliCfg_t *cliCfg,
                             MmwDemo_CliCommonCfg_t *cliCommonCfg,
                             MmwDemo_Cfg *cfg);

/**
 *  @b Description
 *  @n
 *   Initializes data path state variables for 1D processing.
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_dataPathInit1Dstate(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *   Delete Semaphores which are created in MmwDemo_dataPathInitEdma().
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_dataPathDeleteSemaphore(MmwDemo_DSS_dataPathContext_t *context);

/**
 *  @b Description
 *  @n
 *   Initializes EDMA driver.
 *  @retval
 *      Not Applicable.
 */
int32_t MmwDemo_dataPathInitEdma(MmwDemo_DSS_dataPathContext_t *context);

/**
 *  @b Description
 *  @n
 *   Configures EDMA driver for all of the data path processing.
 *  @retval
 *      Not Applicable.
 */
int32_t MmwDemo_dataPathConfigEdma(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *   Configures EDMA driver for data path CQ processing.
 *  @retval
 *      Not Applicable.
 */
int32_t MmwDemo_dataPathConfigCQEdma(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *   Creates heap in L2 and L3 and allocates data path buffers,
 *   The heap is destroyed at the end of the function.
 *
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_dataPathConfigBuffers(MmwDemo_DSS_DataPathObj *obj, uint32_t adcBufAddress);

/**
 *  @b Description
 *  @n
 *   Configures azimuth heat map related processing.
 *
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_dataPathComputeDerivedConfig(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *   Configures FFTs (twiddle tables etc) involved in 1D, 2D and Azimuth processing.
 *
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_dataPathConfigFFTs(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *  Wait for transfer of data corresponding to the last 2 chirps (ping/pong)
 *  to the radarCube matrix before starting interframe processing.
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_waitEndOfChirps(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *    Chirp processing. It is called from MmwDemo_dssDataPathProcessEvents. It
 *    is executed per chirp
 *
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_processChirp(MmwDemo_DSS_DataPathObj *obj, uint16_t chirpIndxInMultiChirp);

/**
 *  @b Description
 *  @n
 *    Interframe processing. It is called from MmwDemo_dssDataPathProcessEvents
 *    after all chirps of the frame have been received and 1D FFT processing on them
 *    has been completed.
 *
 *  @retval
 *      Not Applicable.
 */
void MmwDemo_interFrameProcessing(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *      Power of 2 round up function.
 */
uint32_t MmwDemo_pow2roundup (uint32_t x);

/**
 *  @b Description
 *  @n
 *      Perform error checking for configurations that can change dynamically
 *      after start sensor has been issued e.g multi object, peakGrouping etc
 *      Ideally these checks should be done when the configuration commands are issued
 *      but this blows up code size because for each command there needs to be checking
 *      with current state related to other commands. So doing it in run-time (real-time)
 *      is cheaper with some expenditure of cycles to do the checks. If there is error
 *      exception message will be generated.
 *  @retval
 *     None
 */
void MmwDemo_checkDynamicConfigErrors(MmwDemo_DSS_DataPathObj *obj);

/**
 *  @b Description
 *  @n
 *      Start CQ EDMA
 *  @param[in] obj  Pointer to data path object
 *
 *  @retval
 *      None
 */
void MmwDemo_dssDataPathStartCQEdma(MmwDemo_DSS_DataPathObj *ptrDataPathObj);

#ifdef __cplusplus
}
#endif

#endif /* DSS_DATA_PATH_H */

