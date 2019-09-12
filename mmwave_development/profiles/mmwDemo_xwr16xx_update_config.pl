#This script updates the mmwave profile configuration files
#for the mmwave demo. Valid only for xwr16xx scripts.
#syntax: perl mmwDemo_xwr16xx_update_config.pl <your_cfg_file> 
#output file: <your_cfg_file>_updated

die "syntax: $0   <Input cfg file> \n" if ($#ARGV != 0);
$inputFile = $ARGV[0]; 
$scriptName = $0;
open INPUT, $inputFile or die "Can't open $inputFile\n";
$outputFile = ">" . $inputFile . "_updated";
open OUTPUT, $outputFile or die "\nCan't create file to update config: " . $outputFile."\n";

$scriptVersion = "1.3";

#Fields to be updated with (-1) for subframe configuration.
#This is to be used only to update old commands from the first release that needed to add (-1) for
#subframe configuration. If you just created a new command do not add it to this list.
@fieldsUpdated = 
(
 "adcbufCfg",
 "guiMonitor",
 "cfarCfg",
 "peakGrouping",
 "multiObjBeamForming",
 "clutterRemoval",
 "calibDcRangeSig",
 "extendedMaxVelocity"
);

#number of expected entries for each field
#This is to be used only to update old commands from the first release that needed to add (-1) for
#subframe configuration. If you just created a new command do not add it to this list.
%numEntries = (
 adcbufCfg  => 5,
 guiMonitor => 7, 
 cfarCfg => 8,
 peakGrouping => 6,
 multiObjBeamForming => 3, 
 clutterRemoval => 2,
 calibDcRangeSig => 5,
 extendedMaxVelocity => 2
);

#warning banner
$warningBanner = "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n";

#Comment to be added when a new command is inserted in the script
$newCmdMsg = "\%Inserting new mandatory command. Check users guide for details.\n";

#String appended to the begining of the command
$update_string = " -1";

#Updating the config file to work with visualizer given by the version below
# visualizerVersion = v1.v2.v3
$v1 = 2;
$v2 = 0;
$v3 = 0;
$visualizerVersion = $v1.".".$v2.".".$v3;

#first run through the file to check for missing commands introduced in the latest release
$extendedMaxVelocityFlag = 0;
$nearFieldCfgFlag = 0;
$clutterRemovalFlag = 0;
$calibDcRangeSigFlag = 0;
$rxSatMonFlag = 0;
$sigImgMonFlag = 0;
$analogMonFlag = 0;
$compRangeBiasAndRxChanPhaseFlag = 0;
$measureRangeBiasAndRxChanPhaseFlag = 0;
$bpmCfgFlag = 0;
$lvdsStreamCfgFlag = 0;
$lowPowerCfgFlag = 0;
$missingCmdFlag = 0;
$lineCount = 0;
while (<INPUT>) 
{
    $lineCount++;
    $i = $_;
    if (index($i,"extendedMaxVelocity")>=0 ) 
    {
       $extendedMaxVelocityFlag = 1;
       next;       
    }
    if (index($i,"nearFieldCfg")>=0 ) 
    {
       $nearFieldCfgFlag = 1;
       next;       
    }
    if (index($i,"clutterRemoval")>=0 ) 
    {
       $clutterRemovalFlag = 1;
       next;       
    }
    if (index($i,"calibDcRangeSig")>=0 ) 
    {
       $calibDcRangeSigFlag = 1;
       next;       
    }
    if (index($i,"compRangeBiasAndRxChanPhase")>=0 ) 
    {
       $compRangeBiasAndRxChanPhaseFlag = 1;
       next;       
    }    
    if (index($i,"measureRangeBiasAndRxChanPhase")>=0 ) 
    {
       $measureRangeBiasAndRxChanPhaseFlag = 1;
       next;       
    }    
    if (index($i,"bpmCfg")>=0 ) 
    {
       $bpmCfgFlag = 1;
       next;       
    }
    if (index($i,"lvdsStreamCfg")>=0 ) 
    {
       $lvdsStreamCfgFlag = 1;
       next;       
    }
    if (index($i,"lowPower")>=0 ) 
    {
       #check if low power is enabled. If not, it has to be enabled.
       if ((index($i,"lowPower 0 0")>=0) || (index($i,"lowPower 0  0")>=0) || (index($i,"lowPower  0 0")>=0))
       {
           #command is present but wrong. It needs to be replaced
           $lowPowerCfgFlag = 2;
       }
       else
       {      
           #command is present and OK       
           $lowPowerCfgFlag = 1;
       }    
       next;       
    }
    if (index($i,"CQRxSatMonitor")>=0)
    {
       $rxSatMonFlag = 1;
       next;
    }
    if (index($i,"CQSigImgMonitor")>=0)
    {
       $sigImgMonFlag = 1;
       next;
    }
    if (index($i,"analogMonitor")>=0)
    {
       $analogMonFlag = 1;
       next;
    }    
    if (index($i,"sensorStart")>=0)
    {
       $sensorStartLine = $lineCount;
    }
}

$warningMsg = $warningBanner."The following mandatory command(s) was(were) added to the output script. Check the users guide for details.\n";
if($extendedMaxVelocityFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: extendedMaxVelocity\n";
}
if($nearFieldCfgFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: nearFieldCfg\n";
}
if($clutterRemovalFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: clutterRemoval\n";
}
if($calibDcRangeSigFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: calibDcRangeSig\n";
}
if($analogMonFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: analogMonitor\n";
}
if($sigImgMonFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: CQSigImgMonitor\n";
}
if($rxSatMonFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: CQRxSatMonitor\n";
}
if($compRangeBiasAndRxChanPhaseFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: compRangeBiasAndRxChanPhase\n";
}
if($measureRangeBiasAndRxChanPhaseFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: measureRangeBiasAndRxChanPhase\n";
}
if($bpmCfgFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: bpmCfg\n";
}
if($lvdsStreamCfgFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: lvdsStreamCfg\n";
}
if($lowPowerCfgFlag == 0)
{
    $missingCmdFlag = 1;
    $warningMsg = $warningMsg."Command: lowPower\n";
}
$warningMsg = $warningMsg.$warningBanner;

seek INPUT, 0, 0;

#create output file
print OUTPUT "\%This file was updated by script ",$scriptName," version:",$scriptVersion,"\n";
print OUTPUT "\%This file is compatible with Visualizer Version:",$visualizerVersion,"\n";
$lineCount = 0;
while (<INPUT>) 
{
    #print "$_\n";
    $lineCount++;
    if($lineCount == $sensorStartLine)
    {
        #Lets place here the missing commands, just before sensorStart cmd
        if($extendedMaxVelocityFlag == 0)
        {
            print OUTPUT $newCmdMsg . "extendedMaxVelocity -1 0\n";
        }
        if($nearFieldCfgFlag == 0)
        {
            print OUTPUT $newCmdMsg . "nearFieldCfg -1 0 0 0\n";
        }
        if($clutterRemovalFlag == 0)
        {
            print OUTPUT $newCmdMsg . "clutterRemoval -1 0\n";
        }
        if($calibDcRangeSigFlag == 0)
        {
            print OUTPUT $newCmdMsg . "calibDcRangeSig -1 0 -5 8 256\n";
        }
        if($compRangeBiasAndRxChanPhaseFlag == 0)
        {
            print OUTPUT $newCmdMsg . "compRangeBiasAndRxChanPhase 0.0 1 0 1 0 1 0 1 0 1 0 1 0 1 0 1 0\n";
        }
        if($measureRangeBiasAndRxChanPhaseFlag == 0)
        {
            print OUTPUT $newCmdMsg . "measureRangeBiasAndRxChanPhase 0 1.5 0.2\n";
        }
        if($rxSatMonFlag == 0)
        {
            # These are example configurations
            print OUTPUT $newCmdMsg . "CQRxSatMonitor 0 3 4 13 0\n";
        }
        if($sigImgMonFlag == 0)
        {
            # These are example configurations
            print OUTPUT $newCmdMsg . "CQSigImgMonitor 0 13 4\n";
        }
        if($analogMonFlag == 0)
        {
	    # Disable CQ monitor since the configuration need to be sync with profile cfg
            print OUTPUT $newCmdMsg . "analogMonitor 0 0\n";
        }
        if($bpmCfgFlag == 0)
        {
            print OUTPUT $newCmdMsg . "bpmCfg -1 0 0 1\n";
        }
        if($lvdsStreamCfgFlag == 0)
        {
            print OUTPUT $newCmdMsg . "lvdsStreamCfg -1 0 0 0\n";
        }
        if($lowPowerCfgFlag == 0)
        {
            print OUTPUT $newCmdMsg . "lowPower 0 1\n";
        }
    }

    $i = $_;
    
    #modify lowPower command if low power is not enabled.
    if($lowPowerCfgFlag == 2)
    {
        if (index($i,"lowPower")>=0 )
        {
            $i = "\%Low power must be enabled. Check users guide for details.\nlowPower 0 1\n";
        }        
    }
    
    
    $match = 0;
    foreach $f (@fieldsUpdated)
    {
        if (index($i,$f)>=0 ) 
        {
            @s = split(/ /, $i);
            #Check if this command already has the expected number of entries.
            #Count number of entries ignoring extra blank spaces.
            $numValidEntries = 0;
            for($eIdx = 0; $eIdx < scalar(@s); $eIdx++)
            {
                if(!($s[$eIdx] eq ''))
                {
                    $numValidEntries++;
                }    
            }
            #print "\n",$f," ",$numValidEntries;            
            #In this case, do not update this line.
            if($numValidEntries != ($numEntries{$f} + 1))
            {
                $newLine = $s[0].$update_string;
                for($k=1; $k<scalar(@s); $k++)
                {
                    $newLine = $newLine . " " . $s[$k];   
                }
                print OUTPUT $newLine;
                $match = 1;
            }    
            last;
        }
    }
    if($match == 0)
    {
        # no match with version or with replacement lines. Just copy line to output.
        print OUTPUT $i;        
    }
}
close (INPUT);
close (OUTPUT);
if($missingCmdFlag == 1)
{
    die $warningMsg;
}

