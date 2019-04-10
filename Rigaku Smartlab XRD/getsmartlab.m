%% getsmartlab.m
%
% Loads XRD data from a .ras file output from Rigaku smartlab. Takes the filepath to your .ras
% file as an optional input - if no input is given, UI menu opens to select the file manually.
%
% Outputs data in struct format. Output includes the 2theta values, intensity values, and some scan
% metrics (type of measurement, time, scan speed and resolution)
%
% Example: mydata = getsmartlab     (use UI to select file)
%
%          mydata = getsmartlab('C:\My\XRD\File.ras')   (directly offer filepath)


function [xrd] = getsmartlab(filepath)
    
    header_start = '*RAS_HEADER_START';
    header_end = '*RAS_HEADER_END';
    data_start = '*RAS_INT_START';
    data_end = '*RAS_INT_END';
    
    parameters = {'*MEAS_COND_OPT_ATTR', 'MeasurementCondition';...
                  '*MEAS_SCAN_AXIS_X_INTERNAL', 'ScanAxis';...
                  '*MEAS_SCAN_END_TIME', 'EndTime';...
                  '*MEAS_SCAN_END_TIME', 'StartTime';...
                  '*MEAS_SCAN_SPEED_USER', 'ScanSpeed';...
                  '*MEAS_SCAN_RESOLUTION_X', 'ScanResolution';...
                  };
    
    
              
    %% Code Start
    
    xrd.TwoTheta = [];
    xrd.Counts = [];
    
    if nargin < 1
        [fname, fpath] = uigetfile('*.ras', 'Select .RAS File');
        filepath = fullfile(fpath, fname);
    end
    
    xrd.Parameters.Filepath = filepath;        
    
    fid = fopen(filepath, 'r');
    
    
    nextline = fgetl(fid); 
    while(~strcmp(nextline, header_start))
        nextline = fgetl(fid);
    end
    nextline = fgetl(fid); 
    
    while(~strcmp(nextline, header_end))
        for idx = 1:size(parameters, 1)
            if contains(nextline, parameters{idx, 1})
                xrd.Parameters.(parameters{idx, 2}) = nextline(length(parameters{idx,1}) + 3 : end-1);
                newval = str2double(xrd.Parameters.(parameters{idx, 2}));
                if ~isnan(newval)
                    xrd.Parameters.(parameters{idx, 2}) = newval;
                end
            end
        end            
        nextline = fgetl(fid);
    end
        
    while(~strcmp(nextline, data_start))
        nextline = fgetl(fid);
    end
    nextline = fgetl(fid);
    
    while(~strcmp(nextline, data_end))
        tempdat = textscan(nextline, '%f');
        xrd.TwoTheta = [xrd.TwoTheta; tempdat{1}(1)];
        xrd.Counts = [xrd.Counts; tempdat{1}(2)];
        nextline = fgetl(fid);
    end
    
end