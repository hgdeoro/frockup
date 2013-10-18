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

frockup.controller('GlobalController', function($scope, $location) {

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
