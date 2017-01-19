'use strict';

// controls the list of recipes
app.controller('NewRecipeCtrl', ['$scope', '$http', function($scope, $http) {
    $scope.recipe = {};

    $scope.update = function(recipe) {
      // temporary
      recipe = Object.assign({}, recipe);
      recipe.ingredients = [recipe.ingredients];
      recipe.instructions = [recipe.instructions];

      $http.post('/api/recipe/create', recipe).success(function(data) {
        $scope.ok = true;
        if (data.status === "error") {
            $scope.message = 'Error: ' + data.message;
        } else {
            $scope.message = "Done";
        }
      }).error(function (err) {
        $scope.ok = true;
        $scope.message = "Server error with this request";
      });
    };
}]);