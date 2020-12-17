function insertTableRow(project) {
    // The project here is the response data in Json format
    let table = document.getElementById("projects-table").getElementsByTagName('tbody')[0];
    let rowIndex = table.rows.length;
    let row = table.insertRow(rowIndex);
    row.id = "projectRow_"+project.id;
    row.insertCell(0).innerHTML = "<button onclick=\"deleteProject('" + project.id + "','" + project.name + "')\">Delete</button>";
    row.insertCell(1).innerHTML = "<a href=\'" + project.name + "\\images\'>" + project.name + "</a>";
    row.insertCell(2).innerHTML = project.description;
    row.insertCell(3).innerHTML = project.date.replace("T", " ");
    row.insertCell(4).innerHTML = project.images.length.toString();
    row.insertCell(5).innerHTML = project.iteration;
    // The nubmer of annotated objects are 0 for a new project
    row.insertCell(6).innerHTML = "0"
}

var projectModule = angular.module("myApp", []);
projectModule.controller("myCtrl", function($scope, $http) {

    $scope.addProject = function() {
        this.myForm.$setPristine();
        this.myForm.$setUntouched();
        let data = $scope.formData;
        let time = new Date();
        data["date"] = time.toISOString().substring(0, 19).replace("T", " ");
        $http.post("/api/db/project", data)
            .then(function (response) {
                insertTableRow(response.data)
                resetForm();
            }).catch(function (response) {
            alert('Error when trying to add project: ' + response.data.message);
        });
    };
    $scope.cancelAdd = function() {
        resetForm();
    }
    // Nested function that reset the form data
    function resetForm() {
        try{
            $scope.formData.name = "";
            $scope.formData.description = "";
        } catch (e) {
        }
    }


}); // angular controller


// ask for confirmation and delete the images and/or project
function deleteProject(projectid, projectName) {
    let xhr = new XMLHttpRequest();
    let $dialog = $('<div></div>').html('SplitText').dialog({
        dialogClass: "no-close",
        title: "Delete Project",
        width: 400,
        height: 200,
        modal: true,
        // We have three options here
        buttons: {
            "Delete Project": function () {
                let run_url = "api/db/project/" + projectid;
                $dialog.dialog('close');
                xhr.onreadystatechange = function () {
                    $dialog.dialog('close');
                    if (xhr.readyState == 4) {
                        let table = document.getElementById("projects-table").getElementsByTagName('tbody')[0];
                        let rowIndex =document.querySelector("#projectRow_"+projectid).rowIndex - 1;
                        if (rowIndex >= 0 && rowIndex < table.rows.length) {
                            document.getElementById("projects-table").getElementsByTagName('tbody')[0].deleteRow(rowIndex)
                        } else {
                            alert("Error when trying to add project: '"+projectName+"'!")
                        }
                    }
                };
                xhr.open("DELETE", run_url, true);
                xhr.send();
            },
            // Simply close the dialog and return to original page
            "Cancel": function () {
                $dialog.dialog('close');
            }
        }
    });
    $dialog.html("Do you want to delete the project: '"+projectName+"'?")
} // deleteProject

function init() {
    let formBodyInput = document.getElementById("formBody");
    formBodyInput.addEventListener("keyup", function (event) {
        if (event.keyCode === 13) {
            event.preventDefault();
            document.getElementById("addProjectButton").click()
        }
    });
    $('#addNewProj').on('shown.bs.modal', function() {
        $("#project_name_input").focus();
    });
}
