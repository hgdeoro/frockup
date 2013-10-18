var frockup = angular.module('Frockup', []);

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

frockup.controller('GlobalController', function($scope, $location, $timeout,
		remoteService) {

	$scope.extras = {
		directory : '',
		spinner : false,
		directories : [],
		show_completed : true,
		processing_directory : null,
		background_process_status : null,
	};

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

			localStorage.setItem('frockupDirHistory', JSON
					.stringify(frockupDirHistory));
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

		remoteService.callMethod('load_directory', $scope.extras.directory)
				.success(function(data) {
					$scope.extras.spinner = false;
					$scope.extras.directories = data.ret.directories;
				}).error(function(data) {
					$scope.extras.spinner = false;
					$scope.extras.directories = [];
				});
	};

	$scope.syncDirectory = function(directory) {
		$scope.extras.processing_directory = directory;

		remoteService.callMethod('launch_process').success(function(data) {
		}).error(function(data) {
		});

		$timeout(function() {
			$scope.extras.processing_directory = null;
		}, 2000);
	};

	$scope.getBackgroundProcessesStatus = function() {
		remoteService.callMethod('get_background_process_status').success(
				function(data) {
					$scope.extras.background_process_status = data.ret.message;
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

});

function MainController($scope, $http, $location) {

};
