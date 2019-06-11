%% findxrdpeaks.m
%
%   This function finds xrd peaks in a given pattern, and returns the
%   twotheta values. Also returns normalized intensity of each peak. If a
%   flag is given (0,1) for plotflag, the user can choose to plot the
%   pattern with peaks labeled. peakprominence can be specified in units of
%   counts (not normalized) if the automatically set prominence is not
%   satisfactory.

function [peaks, intensities] = findxrdpeaks(twotheta, counts, plotflag, peakprominence)
    if nargin < 3
        plotflag = 0;
    end
    
    if nargin < 4
        peakprominence = min(counts) + 0.25*std(counts);
    end
    
    [intensities, locs] = findpeaks(counts, 'MinPeakProminence', peakprominence);
    intensities = intensities/max(intensities);
    peaks = twotheta(locs);
    
    if plotflag
        figure, hold on;
        plot(twotheta, counts);
        plot(twotheta(locs), counts(locs), 'rx', 'markersize', 10);
        xlabel('2\Theta (\circ)');
        ylabel('Counts');
    end
end