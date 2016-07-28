angular.module("myApp", ['ngMaterial'])

.config(function($mdThemingProvider) {
  $mdThemingProvider.theme('default')
    .primaryPalette('red')
    .accentPalette('red');
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

.controller('navController', function($scope) {
    $scope.currentNavItem = 'submit';
})

.controller('teslaController', function($scope, $q, $log, $http, $timeout, $window, toaster) {
    $scope.position = "";
    $scope.locating = false;
    $scope.item = undefined;

    $scope.date = new Date();

    var d = new Date();
    d.setSeconds(0,0);
    $scope.time = d;


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
        }
    }

    $scope.submit = function() {
        var d = $scope.date;
        d.setHours($scope.time.getHours());
        d.setMinutes($scope.time.getMinutes());
        d.setSeconds(0, 0);
        $scope.item.time = moment(d);
        $log.info('Submit', $scope.item);
        $scope.submitting = true;

        $http.post('/charging', $scope.item).then(function successCallback(response) {
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
    $scope.searchText = "";
    $scope.items = [];
    $scope.loadHistory = function() {
        $http.get('/charging?query='+$scope.searchText).then(function successCallback(response) {
            $scope.items = response.data;
            $log.info($scope.items);
          }, function errorCallback(response) {
            $log.error(response);
        });
    };

    $scope.loadHistory();
})
;
