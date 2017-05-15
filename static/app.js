angular.module("myApp", ['ngRoute', 'ngCookies', 'ngMaterial', 'gettext', 'suc.charts',])

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

.config(function($routeProvider, $locationProvider) {
    $locationProvider.hashPrefix('');
    $routeProvider
    .when("/overview", {
        templateUrl : "/static/overview.html",
        controller : "overviewController"
    })
    .when("/", {
        templateUrl : "/static/checkin.html"
    })
    .when("/checkin", {
        templateUrl : "/static/checkin.html"
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
        controller : "statsController"
    })
    .when("/stats/superCharger/:superCharger", {
        templateUrl : "/static/stats.html",
        controller : "statsController"
    });
})

.filter('ifEmpty', function() {
    return function(input, defaultValue) {
        if (angular.isUndefined(input) || input === null || input === '') {
            return defaultValue;
        }

        return input;
    }
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

.controller('navController', function($scope, $location, $log, gettextCatalog) {
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

    $scope.overviewUrl = config['overviewUrl'];

    $scope.lang = 'en';
    $scope.switchLanguage = function(lang) {
        $scope.lang = lang;
        gettextCatalog.setCurrentLanguage(lang);
    };
    var supportedLanguages = {'de': true, 'en': true};
    var userLanguages = config['userAgentLanguages'].filter(function(l) { return l in supportedLanguages; })
    $log.info("Auto-detected language userAgentLanguages=", config['userAgentLanguages'], ", userLanguages=", userLanguages);
    if (userLanguages.length > 0) {
        $scope.switchLanguage(userLanguages[0]);
    } else {
        $scope.switchLanguage('en');
    }


    $scope.problemList = {
        "none": "No problems",
        "limitedPower": "Limited power",
        "partialFailure": "Partial failure",
        "completeFailure": "Complete failure",
        "trafficDisruption": "Traffic disruption"
    };
    $scope.getProblemDescr = function(problem) {
        if (problem in $scope.problemList) {
            return $scope.problemList[problem];
        } else {
            return "Missing translation";
        }
    };


    $scope.country = '';
    $scope.superCharger = '';
})

.directive('sucSelector', function($q, $log, $http, $routeParams, $location, $timeout) {
    return {
        restrict : "A",
        templateUrl: '/static/sucSelector.html',
        scope: {
            selectedItem: '=',
            sucId: '@'
        },
        link: function($scope, $elem, $attr) {
            $scope.autoSelect = false;

            if ('locationId' in $routeParams) {
                $log.debug("sucId=", $scope.sucId);
                document.getElementsByTagName("form")[0].focus();
                $scope.$applyAsync(function() {
                    $scope.autoSelect = true;
                    $scope.searchText = $routeParams['locationId'];
                    document.getElementById($scope.sucId).getElementsByTagName("input")[0].focus();
                });
            }

            $scope.position = "";
            $scope.locating = false;

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

                            $scope.autoSelect = true;
                            $scope.searchText = lat.toFixed(3) +","+lng.toFixed(3);
                            document.getElementById($scope.sucId).getElementsByTagName("input")[0].focus();
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

            $scope.querySearch = function(query) {
                deferred = $q.defer();

                $http({
                  method: 'GET',
                  url: '/lookup?query='+query
                }).then(function successCallback(response) {
                    deferred.resolve(response.data);

                    if ($scope.autoSelect) {
                        if (response.data.length == 1) {
                            $scope.selectedItem = response.data[0];
                        }
                        $scope.autoSelect = false;
                    }
                  }, function errorCallback(response) {
                      $log.error(response);
                });

                return deferred.promise;
            }
            $scope.searchTextChange = function(text) {
                $log.info('Text changed to ' + text);
            }
            $scope.selectedItemChange = function(item) {
                $log.info('Item changed to ', item);
            }
        }
    }
})


.directive('stallsSelector', function($q, $log, $http) {
    return {
        restrict : "A",
        templateUrl: '/static/stallsSelector.html',
        scope: {
            nofStalls: '=',
            selected: '=',
        },
        link: function($scope, $elem, $attr) {

            $scope.items = [];
            for (var i = 0; i < $scope.nofStalls / 2; i++) {
                $scope.items.push((i + 1) + "A");
                $scope.items.push((i + 1) + "B");
            }

            $scope.toggle = function(item) {
                var idx = $scope.selected.indexOf(item);
                if (idx > -1) {
                    $scope.selected.splice(idx, 1);
                } else {
                    $scope.selected.push(item);
                }
            };

            $scope.isSelected = function(item) {
                return $scope.selected.indexOf(item) > -1;
            };

            $scope.isIndeterminate = function() {
                return ($scope.selected.length !== 0 && $scope.selected.length !== $scope.items.length);
            };

            $scope.isChecked = function() {
                return $scope.selected.length === $scope.items.length;
            };

            $scope.toggleAll = function() {
                if ($scope.selected.length === $scope.items.length) {
                    $scope.selected = [];
                } else {
                    $scope.selected = $scope.items.slice(0);
                }
            };
        }
    }
})

.controller('overviewController', function($scope, $q, $log, $http, $window, toaster) {
    $scope.sucOverview = [];

    $scope.loading = true;
    $http.get('/overview').then(function successCallback(response) {
        $scope.loading = false;
        $scope.sucOverview = response.data;
    }, function errorCallback(response) {
        $scope.loading = false;
        $log.error(response);
    });


})

.controller('checkinController', function($scope, $q, $log, $http, $window, $routeParams, $cookies, toaster) {
    $scope.suc = undefined;
    $scope.item = undefined;

    $scope.date = new Date();

    var d = new Date();
    d.setSeconds(0,0);
    $scope.time = d;

    if ('tffUserId' in $routeParams) {
        $scope.tffUserId = $routeParams['tffUserId'];
    } else if ($cookies.get('tffUserId') != undefined) {
        $scope.tffUserId = $cookies.get('tffUserId');
    } else {
        $scope.tffUserId = "";
    }

    $scope.$watch('suc', function(newValue, oldValue) {
        $log.info('Item changed to ', newValue);

        if (newValue != undefined) {
            $scope.item = newValue;
            if (newValue.lastCheckin && newValue.lastCheckin.problem) {
                $scope.item.problem = newValue.lastCheckin.problem;
            } else {
                $scope.item.problem = 'none';
            }

            if (newValue.lastCheckin && newValue.lastCheckin.affectedStalls) {
                $scope.item.affectedStalls = newValue.lastCheckin.affectedStalls;
            } else {
                $scope.item.affectedStalls = [];
            }

            if (newValue.lastCheckin && newValue.lastCheckin.notes) {
                $scope.item.notes = newValue.lastCheckin.notes;
            } else {
                $scope.item.notes = "";
            }

            $log.debug("New item", $scope.item);
        }
    });

    /*$scope.$watch('item.affectedStalls', function(newValue, oldValue) {
        if ($scope.item != undefined && $scope.item.problem == 'blockedStalls') {
            $scope.item.blocked = newValue.length;
        }
    }, true);*/

    $scope.submit = function() {
        var d = $scope.date;
        d.setHours($scope.time.getHours());
        d.setMinutes($scope.time.getMinutes());
        d.setSeconds(0, 0);
        $scope.item.time = moment(d);
        $scope.item.tffUserId = $scope.tffUserId;
        $cookies.put('tffUserId', $scope.tffUserId);
        $log.info('Submit', $scope.item);
        $scope.submitting = true;

        $http.post('/checkin', $scope.item).then(function successCallback(response) {
            $scope.submitting = false;
            toaster.showSimpleToast("Submitted, thank you.");
            $window.scrollTo(0, 0);
            $scope.searchText = '';
            $scope.item = undefined;
            $scope.suc = undefined;
          }, function errorCallback(response) {
            $window.scrollTo(0, 0);
            $scope.submitting = false;
            $log.error(response);
            var msg = response.data != undefined && response.data.message != undefined ? response.data.message : response.statusText;
            toaster.showSimpleToast("Failed to submit: " + msg);
        });
    };
})


.controller('historyController', function($scope, $http, $log) {
    $scope.loading = false;
    $scope.filterText = "";
    $scope.items = [];

    $scope.$watch('filterText', function(newValue, oldValue) {
        $scope.loadHistory();
    });

    $scope.loadHistory = function() {
        $scope.loading = true;
        $http.get('/checkin?limit=50&filter='+$scope.filterText).then(function successCallback(response) {
            $scope.loading = false;
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
            $scope.superChargerStatsEmpty = $scope.superChargerStats.every(function(d) { return d.charging == null });

            console.log('superChargerStats=', $scope.superChargerStats, ', superChargerStatsEmpty=', $scope.superChargerStatsEmpty);
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
