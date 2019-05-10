function plotxrdoffset(scans)
%% Parameters
    offset = 1;


%% Code Start
    figure, hold on;
    for idx = 1:numel(scans)
        normalized_counts = scans(idx).Counts/max(scans(idx).Counts);
        normalized_counts = normalized_counts + offset*(idx-1);
        plot(scans(idx).TwoTheta, normalized_counts);
    end
end