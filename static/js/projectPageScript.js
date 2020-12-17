// main page logic
var mainPage = angular.module('projectPage', ['ui.bootstrap', 'angular-tour', 'ngCookies'])
.controller('imageSelector', ['$scope', ($scope) => {
    // Variables
    $scope.project = project;
    $scope.images = images;
    $scope.sortMethod = 'name';
    $scope.ascending = false;

    function addImage(img) { 
        $scope.images.push(img);
        $scope.$apply();
    }

    // Sorting Comparator
    $scope.comparator = (a, b) => {
        if($scope.sortMethod === 'name') {
            // Sort by name
            if(a.name < b.name) return -1;
            if(a.name > b.name) return 1;
            return 0;
        }
        else if($scope.sortMethod === 'rois') {
            // Sort by # annotated ROIs
            return a - b;
        }
        else if($scope.sortMethod === 'edit') {
            // Sort by last modified date
            return new Date(a.date) - new Date(b.date);
        }
    };

    // Drag & Drop file upload setup
    angular.element(document).ready(function() {
        Dropzone.options.uploadFiles = {
            init: function () {
                this.on("complete", function (file) {
                    if (this.getUploadingFiles().length === 0 && this.getQueuedFiles().length === 0) {
                        for(let file of this.getAcceptedFiles()) {
                            addImage({
                                name: file.name,
                                height: file.height,
                                width: file.width,
                                ROIs: 0, // default
                                pixelsAnnotated: 0 // default
                            });
                            this.removeFile(file);
                        }
                    }
                });
            }
        };
    });
}]);

// tour logic
mainPage.controller('tourController', ['$scope', '$cookies', '$timeout', ($scope, $cookies, $timeout) => {
    var cookieName = 'projectPageTourStep';

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