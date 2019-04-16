%loads all spectra from an output save folder from the Lambda 1050
%spectrophotometer in the SME basement. If any argument is passed, it will
%attempt to sort spectra by "Cycle#'. This is only relevant in diffusion experiment setup(ie, if cycles are
%set to > 1, and if all cycles are in one series. If you have 10 samples
%with 3 cycle each, this function will break. Don't use any argument in
%this case).
%
%  ex: mydata = getlambdadata    (opens UI to select folder, loads all spectra files within the folder)
%      mydata = getlambdadata(1) (opens UI to select folder, loads all spectra files within folder, then sorts by cycle number)
%
%      outputs data in struct format

function output = getlambdadata(~)

    checkstring = '.Raw.csv';
    omitstring = 'Baseline';
    sortspec = 0;
    
    if nargin > 0
        sortspec = 1;
    end
    
    folder = uigetdir();    
%     folder = 'E:\Data\MRC Spec\Rishi Kumar\20180323';
    topdir = dir(folder);    
    numfiles = size(topdir, 1);
    
    dataindex = 1;
    
    for i = 1:numfiles
        subpath = fullfile(folder, topdir(i).name);
        if (contains(subpath, checkstring) && ~contains(subpath, omitstring))
                    fname = topdir(i).name;
                    name_split = strsplit(fname, '.Sample');
                    if(contains(name_split{2}, 'Cycle'))
                        cycle_split = strsplit(name_split{2}, '.');
                        output(dataindex).title = horzcat(name_split{1}, ' ', cycle_split{2});
                    else
                        output(dataindex).title = name_split(1);
                    end
                    spectrum = csvread(subpath, 1, 0);
                    output(dataindex).wavelengths = spectrum(:,1);
                    output(dataindex).signal = spectrum(:,2);
                    output(dataindex).filename = fname(1:end);
                    output(dataindex).filepath = fullfile(folder, topdir(i).name, subpath);
                    dataindex = dataindex + 1;
        end                  
    end
        
    
%     %sort spectra taken in multiple cycles
    if sortspec
        specorder = zeros(size(output));
        specnum = specorder;
        startcutoff = '.Cycle';
        endcutoff = 'Raw.csv';
        output_old = output;
        for i = 1:numel(output)
            startidx = strfind(output(i).filename, startcutoff)+length(startcutoff);
            endidx = strfind(output(i).filename, endcutoff)-1;
            specnum(i) = str2double(output(i).filename(startidx:endidx));
        end
        
        for i = 1:numel(output)
            output(i) = output_old(i == specnum);
        end
    end
end
       