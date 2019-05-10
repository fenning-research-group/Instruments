function output = gettracer(filepath)

    if nargin < 1
        [fname, fpath] = uigetfile('*.txt', 'Select ReRa Tracer Output File');
        filepath = fullfile(fpath, fname);
    end

    fid = fopen(filepath,'r');
    output = struct();
    
    fgetl(fid);
    linedata{1,1} = fgetl(fid);
    linedata{1,2} = 'Device';
    linedata{1,3} = 'Title';
    
    curvetype_line = fgetl(fid);
%     curvetype_idx = strfind(curvetype_line, 'Curve');
%     curvetype_idx = [curvetype_idx, numel(curvetype_idx)];
    linedata{2,1} = fgetl(fid);
    linedata{2,2} = 'Size [cm2]';
    linedata{2,3} = 'Area';
    
    fgetl(fid);
    fgetl(fid);
    
    linedata{3,1} = fgetl(fid);
    linedata{3,2} = 'Date';
    linedata{3,3} = 'Date';
    
    linedata{4,1} = fgetl(fid);
    linedata{4,2} = 'Time';
    linedata{4,3} = 'Time';
    
    fgetl(fid);
    
    linedata{5,1} = fgetl(fid);
    linedata{5,2} = 'Irradiance [W/m2]';    
    linedata{5,3} = 'Irradiance';    
    
    fgetl(fid);
    fgetl(fid);
    
    convert_to_num = [0, 1, 0, 0, 1];
    
    for i = 1:size(linedata, 1)
        output = parse_file(linedata{i,1}, linedata{i,2}, output, linedata{i,3}, convert_to_num(i));
    end
    
    num_scans = numel(output);
    
    scan_base = '%f\t%f\t%f\t';
    scan_str = [];
    
    for i = 1:num_scans
        scan_str = [scan_str, scan_base];
    end
    data_raw = textscan(fid, scan_str);
    
    for i = 1:num_scans
        output(i).Voltage = data_raw{3*i-2};
        output(i).Current = data_raw{3*i-1};
        output(i).Power = data_raw{3*i};
    end    
end
    

function output = parse_file(raw, delimiter, output, categorytitle, convert_to_num)
    idx = strfind(raw, delimiter);
    num = numel(idx);
    idx = [idx, numel(raw)];
    for i = 1:num
        value = strtrim(raw(idx(i)+numel(delimiter):idx(i+1)-1));
        if convert_to_num
            value = str2num(value);
        end
        output(i).(categorytitle) = value;
    end
end