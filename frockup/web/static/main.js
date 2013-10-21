var frockup = angular.module('Frockup', [ 'ngRoute', 'ngAnimate' ]);

frockup.config(function($routeProvider) {

    $routeProvider.when('/', {
        controller : MainController,
        templateUrl : '/static/main.html',

    // }).when('/connection', {
    // controller : ConnectController,
    // templateUrl : '/static/app/connect.html',

    // }).when('/pins', {
    // controller : PinsController,
    // templateUrl : '/static/app/pins.html',

    // }).otherwise({
    // controller : aController,
    // templateUrl : '/path/to/template',

    });

});

frockup.factory('remoteService', function($http) {

    var remoteService = {

        callMethod : function(methodName) {
            // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions_and_function_scope/arguments
            var functionArgs = Array.prototype.slice.call(arguments, 1);
            return $http.post('/callMethod/', {
                functionName : methodName,
                functionArgs : functionArgs
            });
        },

    };

    // factory function body that constructs shinyNewServiceInstance
    return remoteService;
});

frockup.controller('GlobalController', function($scope, $location, $timeout, $interval, remoteService) {

    $scope.extras = {
        directory : '',
        spinner : false,
        directories : [],
        show_completed : true,
        processing_directory : null,
        background_process_status : 'Not checked yet',
        extended_status : null,
        alerts : [],
    };

    /*
     * Alerts
     */
    $scope.closeAlert = function(index) {
        $scope.extras.alerts.splice(index, 1);
    };

    $scope.addErrorAlert = function(message) {
        $scope.extras.alerts.push({
            msg : message,
            type : 'danger'
        });
    };

    $scope.addSuccessAlert = function(message) {
        $scope.extras.alerts.push({
            msg : message,
            type : 'success'
        });
    };

    $scope.addInfoAlert = function(message) {
        $scope.extras.alerts.push({
            msg : message,
            type : 'info'
        });
    };

    $scope.addWarningAlert = function(message) {
        $scope.extras.alerts.push({
            msg : message,
            type : 'warning'
        });
    };

    /*
     * 
     */
    $scope.addDirToLocalHistory = function(directory) {
        var frockupDirHistory = localStorage.getItem('frockupDirHistory');
        if (frockupDirHistory == null) {
            frockupDirHistory = [];
        } else {
            frockupDirHistory = JSON.parse(frockupDirHistory);
        }

        if (frockupDirHistory.indexOf(directory) == -1) {
            frockupDirHistory.push(directory);
            frockupDirHistory.sort();

            localStorage.setItem('frockupDirHistory', JSON.stringify(frockupDirHistory));
        }

    };

    $scope.getLocalHistoryDirs = function() {
        return JSON.parse(localStorage.getItem('frockupDirHistory'));
    };

    $scope.resetLocalHistoryDirs = function() {
        localStorage.removeItem('frockupDirHistory');
    };

    $scope.checkDirectory = function() {

        $scope.safeApply(function() {
            $scope.extras.spinner = true;
        });

        $scope.addDirToLocalHistory($scope.extras.directory);

        remoteService.callMethod('load_directory', $scope.extras.directory).success(function(data) {
            $scope.extras.spinner = false;
            $scope.extras.directories = data.ret.directories;
        }).error(function(data) {
            $scope.extras.spinner = false;
            $scope.extras.directories = [];
        });
    };

    $scope.syncDirectory = function(directory) {
        remoteService.callMethod('launch_backup', directory.name).success(function(data) {
            console.info("launch_backup() OK");
            if (data.ret.ok)
                $scope.addSuccessAlert("" + data.ret.message);
            else
                $scope.addErrorAlert("" + data.ret.message);
        }).error(function(data) {

            if (data && data.ret && data.ret.message)
                $scope.addErrorAlert("" + data.ret.message);
            else
                $scope.addErrorAlert("Couldn't launch backup");
        });

    };

    $scope.getBackgroundProcessesStatus = function() {
        remoteService.callMethod('get_background_process_status').success(function(data) {
            $scope.extras.extended_status = null;
            $scope.extras.background_process_status = data.ret.message;
            if (data && data.ret && data.ret.proc_status) {
                var i;
                var msg = "";
                for (i = 0; i < data.ret.proc_status.length; i++) {
                    msg += "[" + data.ret.proc_status[i].pid + "] " + data.ret.proc_status[i].status + "\n";
                }
                $scope.extras.extended_status = msg;
            }
        }).error(function(data) {
            $scope.extras.background_process_status = "Couldn't get status.";
        });

    };

    $scope.isCurrentPath = function(path) {
        return $location.path() == path;
    };

    $scope.safeApply = function(fn) {
        var phase = this.$root.$$phase;
        if (phase == '$apply' || phase == '$digest') {
            if (fn && (typeof (fn) === 'function')) {
                fn();
            }
        } else {
            this.$apply(fn);
        }
    };

    $scope.intervalCheckBackgroundProcesses = $interval(function() {
        $scope.getBackgroundProcessesStatus();
    }, 1000);

});

function MainController($scope, $http, $location) {

};
