/**
 * AngularJS wrapper for Google Visualization Charts
 * c.f. https://developers.google.com/chart/interactive/docs/
 */

var app = angular.module('suc.charts', [])

app.factory('GoogleChartService', function($q) {
    var service = {}
    var isLibraryLoaded = false;

    service.loadLibrary = function() {
        var deferred = $q.defer()

        if (isLibraryLoaded) {
            deferred.resolve()
        } else {
            $.getScript("https://www.google.com/jsapi").done(function(script, textStatus) {
                try {
                    google.load('visualization', '1.1', {
                        'callback': function() {
                            isLibraryLoaded = true;
                            deferred.resolve();
                        },
                        'packages':['corechart', 'annotationchart']
                    });

                } catch(e) {
                    isLibraryLoaded = false;
                    deferred.reject(e);
                }
            }).fail(function(jqxhr, settings, e) {
                isLibraryLoaded = false;
                deferred.reject(exception);
            });
        }

        return deferred.promise;
    };

    return service;
});

app.directive("googleChart",function($window, GoogleChartService) {
    return{
        restrict : "A",
        scope: {
            chartType: '@',
            chartData: '=',
            chartOptions: '=',
            chartXTitle: '@?',
            chartYTitle: '@?',
        },
        link: function($scope, $elem, $attr){

            var drawChart = function() {
                if ($scope.chartData) {
                    var googleChart = new google.visualization[$scope.chartType]($elem[0]);
                    var data = google.visualization.arrayToDataTable($scope.chartData, !$scope.chartOptions.my_firstRowContainsLabels);

                    var options = $.extend({}, $scope.chartOptions);
                    if ($scope.chartXTitle) {
                        $.extend(true, options, {hAxis: {title: $scope.chartXTitle}});
                    }
                    if ($scope.chartYTitle) {
                        $.extend(true, options, {vAxis: {title: $scope.chartYTitle}});
                    }

                    googleChart.draw(data, options);
                }
            };

            var onLibraryLoaded = function() {
                drawChart();
                $scope.$watchCollection('chartData', drawChart);
                $scope.$watchCollection('chartOptions', drawChart);
                angular.element($window).on('resize', drawChart);
            };

            var onLibraryLoadingFailed = function(exception) {
                console.error("Failed to load Google Chart Library", exception);
            };

            GoogleChartService.loadLibrary().then(onLibraryLoaded, onLibraryLoadingFailed);
        }
    }
});