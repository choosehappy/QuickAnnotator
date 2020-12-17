// Main page logic
var mainPage = angular.module('myApp', ['ui.bootstrap', 'angular-tour', 'ngCookies'])
.controller('myCtrl', ['$scope', '$http', '$uibModal', ($scope, $http, $uibModal) => {
    $scope.projects = []; // List of projects (from server)

    // Get project list from server
    $http.get("/api/project").then((response) => $scope.projects = response.data.objects);

    // Modal controls
    $scope.openPopup = function() {
        let modal = $uibModal.open({
            templateUrl: 'template.html',
            controller: 'modalCtrl'
        });
        modal.result.then((project) => $scope.projects.push(project));
    };

    $scope.deleteProject = function(project){
        $http.delete(`api/project/${project.id}`).then((response) => {
            $scope.projects.splice($scope.projects.indexOf(project), 1);
            $http.get(`/${project.name}/delete`); // Also delete the project folder
        });
    };
}]);

// tour logic
mainPage.controller('tourController', ['$scope', '$cookies', '$timeout', ($scope, $cookies, $timeout) => {
    console.log('initial cookies: ', $cookies.getAll());
    var cookieName = 'indexTourStep';

    // the 'play tour' button
    $('#play-tour-btn').click(function() {
        $timeout(function() { // note that this has to be timeout to ensure it gets queued
            // reset the tour to the beginning, then start it
            $scope.currentStep = 0;
            $cookies.put(cookieName, $scope.currentStep);
            $('#tour #tour-close').click();
            $('#tour #tour-reset').click();
            $('#tour #tour-open').click();
        }, 10);
        this.blur();
    });

    // cookie control for the tour
    var curStep = $cookies.get(cookieName);
    if (typeof curStep === 'string')
        curStep = parseInt(curStep);
    $scope.currentStep = curStep || 0;

    $scope.tourComplete = function() {
        $cookies.put(cookieName, -1);
    };

    // update the cookie each time we step through the tour
    $scope.stepComplete = function() {
        $cookies.put(cookieName, $scope.currentStep);
    };
}]);

// Modal logic
var modals = angular.module('myApp')
.controller('modalCtrl', ['$scope', '$http', '$uibModalInstance', ($scope, $http, $uibModalInstance) => {
    $scope.formData = {}; // Data from user when adding new project

    // Logic to close the modal
    $scope.close = () => $uibModalInstance.dismiss();

    $scope.submit = function() {
        $scope.formData.date = new Date().toISOString();
        $http.post('/api/project', $scope.formData).then((response) => {
            $uibModalInstance.close(response.data);
        });
    };

}]);