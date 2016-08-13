angular.module("myApp", ['ngRoute', 'ngMaterial', 'suc.charts',])

.config(function($mdThemingProvider) {
  $mdThemingProvider.theme('default')
    .primaryPalette('red')
    .accentPalette('red');
})
.config(function($mdProgressCircularProvider) {
  $mdProgressCircularProvider.configure({
    progressSize: 20,
  });
})

.config(function($routeProvider) {
    $routeProvider
    .when("/", {
        templateUrl : "/static/checkin.html"
        //controller : "checkinController"
    })
    .when("/history", {
        templateUrl : "/static/history.html",
        controller : "historyController"
    })
    .when("/stats", {
        templateUrl : "/static/stats.html",
        controller : "statsController"
    })
    .when("/stats/country/:country", {
        templateUrl : "/static/stats.html",
        //controller : "statsCountryController"
        controller : "statsController"
    })
    .when("/stats/superCharger/:superCharger", {
        templateUrl : "/static/stats.html",
        //controller : "statsSuCController"
        controller : "statsController"
    });
})

.service('toaster', function($mdToast) {
    var last = {
      bottom: false,
      top: true,
      left: true,
      right: false
    };
    var toastPosition = angular.extend({},last);
    function getToastPosition() {
        sanitizePosition();
        return Object.keys(toastPosition)
          .filter(function(pos) { return toastPosition[pos]; })
          .join(' ');
    };
    function sanitizePosition() {
        var current = toastPosition;
        if ( current.bottom && last.top ) current.top = false;
        if ( current.top && last.bottom ) current.bottom = false;
        if ( current.right && last.left ) current.left = false;
        if ( current.left && last.right ) current.right = false;
        last = angular.extend({},current);
    }

    this.showSimpleToast = function(text) {
        var pinTo = getToastPosition();
        $mdToast.show(
            $mdToast.simple()
                .textContent(text)
                .position(pinTo)
                .hideDelay(3000)
        );
    };
})

.controller('navController', function($scope, $location, $log) {
    $scope.defaultNavItem = 'checkin';

    $scope.updateNav = function() {
        var p = $location.path().split('/');
        $scope.currentNavItem = (p.length < 2 || p[1] == "") ? $scope.defaultNavItem : p[1];
    };

    $scope.$on('$locationChangeSuccess', function(event, newUrl) {
        $log.debug('locationChangeSuccess ' + $location.path());
        $scope.updateNav();
    });

    $scope.updateNav();

    $log.debug('start currentNavItem=' + $scope.currentNavItem);

    $scope.country = '';
    $scope.superCharger = '';
})

.controller('checkinController', function($scope, $q, $log, $http, $timeout, $window, toaster) {
    $scope.position = "";
    $scope.locating = false;
    $scope.item = undefined;

    $scope.date = new Date();

    var d = new Date();
    d.setSeconds(0,0);
    $scope.time = d;

    $scope.tffUserId = "";


    $scope.locate = function() {
        $log.info("locating...")
        $scope.position = "locating...";
        if (navigator.geolocation) {
            $scope.locating = true;
            navigator.geolocation.getCurrentPosition(function(position){
                var lat = position.coords.latitude;
                var lng = position.coords.longitude;
                $log.info("position=", position.coords);
                $scope.$apply(function(){
                    $scope.position = [lat, lng];
                    $scope.locating = false;

                    $scope.searchText = lat.toFixed(3) +","+lng.toFixed(3);
                    document.getElementById('auto_complete_id').getElementsByTagName("input")[0].focus();

                    /*$http({
                      method: 'GET',
                      url: '/lookup/'+lat+"/"+lng
                    }).then(function successCallback(response) {
                        $scope.triggerAutoComplete(response.data);
                      }, function errorCallback(response) {
                          $log.error(response);
                      });*/
                });
            }, function(error) {
                $log.info(error);
                $scope.locating = false;
            });
        } else {
            $log.error("navigator.geolocation not available")
        }
    }

    $scope.searchText = '';
    var self = this;

    self.querySearch   = querySearch;
    self.selectedItemChange = selectedItemChange;
    self.searchTextChange   = searchTextChange;

    // ******************************
    // Internal methods
    // ******************************
    function querySearch(query) {
        deferred = $q.defer();

        $http({
          method: 'GET',
          url: '/lookup?query='+query
        }).then(function successCallback(response) {
            deferred.resolve(response.data);
          }, function errorCallback(response) {
              $log.error(response);
        });

        return deferred.promise;
    }
    function searchTextChange(text) {
        $log.info('Text changed to ' + text);
    }
    function selectedItemChange(item) {
        $log.info('Item changed to ', item);

        if (item !== undefined) {
            $scope.item = item;
            $scope.item.blocked = 0;
            $scope.item.waiting = 0;
            $scope.item.notes = "";
        }
    }

    $scope.submit = function() {
        var d = $scope.date;
        d.setHours($scope.time.getHours());
        d.setMinutes($scope.time.getMinutes());
        d.setSeconds(0, 0);
        $scope.item.time = moment(d);
        $scope.item.tffUserId = $scope.tffUserId;
        $log.info('Submit', $scope.item);
        $scope.submitting = true;

        $http.post('/checkin', $scope.item).then(function successCallback(response) {
            $scope.submitting = false;
            toaster.showSimpleToast("Submitted, thank you.");
            $window.scrollTo(0, 0);
            $scope.searchText = '';
            $scope.item = undefined;
          }, function errorCallback(response) {
            $scope.submitting = false;
            $log.error(response);
            toaster.showSimpleToast("Failed to submit: " + response.statusText);
        });
    }
})


.controller('historyController', function($scope, $http, $log) {
    $scope.loading = false;
    $scope.filterText = "";
    $scope.items = [];

    $scope.$watch('filterText', function(newValue, oldValue) {
        $scope.loadHistory();
    });

    $scope.loadHistory = function() {
        $scope.locating = true;
        $http.get('/checkin?limit=50&filter='+$scope.filterText).then(function successCallback(response) {
            $scope.locating = false;
            $scope.items = response.data;
          }, function errorCallback(response) {
            $scope.locating = false;
            $log.error(response);
        });
    };

    // for some reason the watch on filterText is also triggered when the template is loaded, so we can omit this call
    //$scope.loadHistory();
})

.controller('statsController', function($scope, $http, $log, $location, $routeParams) {
    $scope.loading = false;

    $scope.countries = [];
    $scope.superChargers = [];

    $log.info("stats init country=" + $scope.$parent.country + ", superCharger=" + $scope.$parent.superCharger);

    /* not needed since statsController is re-initialized for each /stats/.. route
    $scope.$on('$locationChangeSuccess', function(event, newUrl) {
        $log.debug('locationChangeSuccess ' + $location.path());
        $scope.updateRoute();
    });*/

    $scope.updateRoute = function() {
        if ('country' in $routeParams) {
            $scope.$parent.country = $routeParams.country;
            $scope.$parent.superCharger = undefined;
            $scope.loadCountry();
        } else if ('superCharger' in $routeParams) {
            $scope.$parent.superCharger = $routeParams.superCharger;
            $scope.loadSuperCharger();
        } else {
            $scope.$parent.country = undefined;
            $scope.$parent.superCharger = undefined;
            $scope.loadStats();
        }
        $log.info("stats country=" + $scope.$parent.country + ", superCharger=" + $scope.$parent.superCharger);
    };


    $scope.loadStats = function() {
        $http.get('/stats').then(function successCallback(response) {
            $scope.countries = response.data;
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    $scope.loadCountry = function() {
        $scope.loading = true;
        $http.get('/stats/country/' + $scope.$parent.country).then(function successCallback(response) {
            $scope.loading = false;
            $scope.superChargers = response.data;
        }, function errorCallback(response) {
            $scope.loading = false;
            $log.error(response);
        });
    };

    $scope.loadSuperCharger = function() {
        $scope.loading = true;
        $http.get('/stats/superCharger/' + $scope.$parent.superCharger).then(function successCallback(response) {
            $scope.loading = false;
            $scope.superChargerTitle = response.data.title;
            if ($scope.$parent.country != response.data.country) {
                $scope.$parent.country = response.data.country;
            }
            var r = response.data.items.map(function (d) {
                return [moment(d.time).toDate(), d.stalls, d.charging, d.blocked, d.waiting];
            });
            r.unshift(["Time", "Stalls", "Charging", "Blocked", "Waiting"]);
            $scope.superChargerStats = r;
            console.log('superChargerStats', $scope.superChargerStats);
        }, function errorCallback(response) {
            $scope.loading = false;
            $log.error(response);
        });
    };

    $scope.superChargerChartOptions = {
        my_firstRowContainsLabels: true,
        displayAnnotations: true
    };

    $scope.updateRoute();
})

;
