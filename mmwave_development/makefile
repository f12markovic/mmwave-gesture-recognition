###################################################################################
# mmWave Demo Level makefile
###################################################################################
ifeq ($(CCS_MAKEFILE_BASED_BUILD), 1)
ifeq ($(OS),Windows_NT)
include $(MMWAVE_SDK_INSTALL_PATH)/scripts/windows/setenv.mak
else
include $(MMWAVE_SDK_INSTALL_PATH)/scripts/unix/setenv.mak
endif
endif

include $(MMWAVE_SDK_INSTALL_PATH)/ti/common/mmwave_sdk.mak
include ./mss/mss_mmw.mak
include ./dss/dss_mmw.mak

MMW_DEMO_BIN         = $(MMWAVE_SDK_DEVICE_TYPE)_mmw_demo.bin
MMW_DEMO_SECURE_BIN  = $(MMWAVE_SDK_DEVICE_TYPE)_mmw_demo_secure.bin

###################################################################################
# Standard Targets which need to be implemented by each mmWave SDK module. This
# plugs into the release scripts.
###################################################################################
.PHONY: all clean mmwDemoClean mmwDemo
.NOTPARALLEL:

# Clean: This cleans all the objects
mmwDemoClean: mssDemoClean dssDemoClean
	@$(DEL) $(MMW_DEMO_BIN)
	@$(DEL) $(MMW_DEMO_SECURE_BIN)

# This builds all the supported demos
mmwDemo: mssDemo dssDemo
	@$(GENERATE_METAIMAGE) $(MMW_DEMO_BIN) 0x00000006 $(MSS_MMW_DEMO_BIN) $(XWR16XX_RADARSS_IMAGE_BIN) $(DSS_MMW_DEMO_BIN)
	@$(DEL) $(MSS_MMW_DEMO_BIN) $(DSS_MMW_DEMO_BIN)
	@$(GENERATE_HS_METAIMAGE) $(MMW_DEMO_SECURE_BIN) 0x00000006 $(MSS_MMW_DEMO_OUT) $(XWR16XX_RADARSS_IMAGE_BIN) $(DSS_MMW_DEMO_OUT) $(MMWAVE_SECDEV_HSIMAGE_CFG)
	@$(DEL) $(MSS_MMW_DEMO_BIN) $(DSS_MMW_DEMO_BIN)
	@echo '******************************************************************************'
	@echo 'Built the mmw Demo Flash Binary '
	@echo '******************************************************************************'


# Clean: This cleans all the objects
clean: mmwDemoClean

# This builds all the supported demos
all: mmwDemo

# Help: This displays the MAKEFILE Usage.
help:
	@echo '****************************************************************************************'
	@echo '* Makefile Targets for the DEMO '
	@echo 'mmwDemo         -> Builds the mmw Demo (both MSS and DSS binaries)'
	@echo 'mmwDemoClean    -> Cleans the mmw Demo (both MSS and DSS binaries)'
	@echo 'mssDemo         -> Builds the MSS binary for the mmw Demo'
	@echo 'mssDemoClean    -> Cleans the MSS binary for mmw Demo '
	@echo 'dssDemo         -> Builds the DSS binary for the mmw Demo'
	@echo 'dssDemoClean    -> Cleans the DSS binary for mmw Demo '
	@echo '****************************************************************************************'

