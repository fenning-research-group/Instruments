function plotxrdoffset(scans, offset)
%% Parameters
    offset_default = 1;


%% Parse Inputs
    if nargin < 2
        offset = offset_default;
    end
    
%% Code Start
    figure, hold on;
    for idx = 1:numel(scans)
        normalized_counts = scans(idx).Counts/max(scans(idx).Counts);
        normalized_counts = normalized_counts + offset*(idx-1);
        plot(scans(idx).TwoTheta, normalized_counts);
    end
    
    xlabel('Two Theta (\circ)');
    ylabel('Normalized Counts')
end