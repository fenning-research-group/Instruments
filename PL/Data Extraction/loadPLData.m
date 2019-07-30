function PLdat = loadPLData(incident_wavelength, title, dirpath)

% laser wavelengths available on renishaw raman tool in MRC: 457, 488, 514,
% 633, 785 nm
renishaw_wavelengths = [457, 488, 514, 633, 785];

if ~any(incident_wavelength == renishaw_wavelengths)
    error('Invalid laser wavelength supplied: Available wavelengths on Renishaw = [457, 488, 514, 633, 785] nm');
end

PLdat.incidentwavelength = incident_wavelength;

%% Load raman data
if nargin < 3
    dirpath = uigetdir('..');
end 

fids = dir(dirpath);

if nargin < 2
    [~, title] = fileparts(dirpath); %if no title is provided, use the folder name as the title
end

PLdat.title = title;
PLdat.filepath = dirpath;

%% generate data matrix
%first pass through the file name list to extract x/y ranges

ignore_flags = {'.', '..', 'desktop.ini', 'Icon'};  % files with titles matching any of these strings are ignored
all_xvals = [];
all_yvals = [];
bad_fids_idx = [];
for idx = 1:length(fids)
    if ~any(strcmp(fids(idx).name, ignore_flags))
        % get x value from file name
        tempstr = strsplit(fids(idx).name, '__X_');
        tempstr = strsplit(tempstr{2}, '__');
        all_xvals = [all_xvals; str2double(tempstr{1})];
        % get y value from file name
        tempstr = strsplit(fids(idx).name, '__Y_');
        tempstr = strsplit(tempstr{2}, '__');
        all_yvals = [all_yvals; str2double(tempstr{1})];
    else
        bad_fids_idx = [bad_fids_idx; idx]; %mark file id index for removal, since it contained an ignore flag
    end
end

fids(bad_fids_idx) = [];    %remove file ids with ignored flags

xvals = sort(unique(all_xvals));
yvals = sort(unique(all_yvals));


%% fill output structure with raman spectra

data(1:numel(yvals), 1:numel(xvals)) = struct( 'x', [],...
                                                'y', [],...
                                                'wavelength', [],...
                                                'counts', [],...
                                                'peak', struct( 'wavelength', [],...
                                                                'counts', []...
                                                                )...
                                                );

hwb = waitbar(0, 'Loading data...');
updateinterval = 25;

tic;
for idx = 1:length(fids)
    if ~mod(idx, updateinterval)
        waitbar(idx/length(fids), hwb, sprintf('Time Remaining: %.2f seconds', toc * (length(fids)-idx) / updateinterval));
        tic;
    end
    if ~any(strcmp(fids(idx).name, ignore_flags))
        m = find(yvals == all_yvals(idx));
        n = find(xvals == all_xvals(idx));
        
        fpath = fullfile(fids(idx).folder, fids(idx).name);
        
%         tempdat = importdata(fpath);
        fid = fopen(fpath);
        tempdat = textscan(fid, '%d\t%d');
        tempdat = double([tempdat{1}, tempdat{2}]);
        fclose(fid);
        
        tempdat(tempdat(:,2) == 0, :) = []; %discard any zero values, assuming that this means the detector is saturated and reading garbage zero values
        
        data(m,n).x = all_xvals(idx);
        data(m,n).y = all_yvals(idx);
        data(m,n).wavelength = tempdat(:,1);
        data(m,n).counts = tempdat(:,2);
        
        %fit emission peak, get peak wavelength + counts
        
        try
            tempfit = fit(data(m,n).wavelength, data(m,n).counts, 'gauss1');
            prevfit = tempfit;
        catch
            tempfit = prevfit;
        end
        
        data(m,n).peak.wavelength = tempfit.b1;
        data(m,n).peak.counts = tempfit.a1;
        
    end    
end

PLdat.data = data;

close(hwb);

end


%converts a raman shift (cm-1) to the emission wavelength (nm) given the
%incident wavelength (nm). positive shift = stokes shift (to lower
%wavenumber)
function emitted = shift_to_wl(shift, incident)
    incident_wavenumber = 1./(incident * 1e-7);
    emitted_wavenumber = incident_wavenumber - shift;
    emitted = 1e7./(emitted_wavenumber);
end