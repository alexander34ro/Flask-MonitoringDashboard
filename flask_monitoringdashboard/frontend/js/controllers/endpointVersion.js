export function EndpointVersionController($scope, $http, infoService, endpointService,
                                   menuService, formService, plotlyService, $filter) {
    endpointService.reset();
    menuService.reset('endpoint_version');
    endpointService.onNameChanged = function (name) {
        $scope.title = 'Per-Version Performance for ' + name;
    };

    // Set the information box
    infoService.axesText = 'The X-axis presents the execution time in ms. The Y-axis presents the versions that are used.';
    infoService.contentText = 'This graph shows a horizontal boxplot for the versions that are used. With this ' +
        'graph you can find whether the performance changes across different versions.';

    formService.clear();
    formService.addVersions(endpointService.info.id);

    formService.setReload(function () {

        $http.post('api/endpoint_versions/' + endpointService.info.id, {
            data: {
                versions: formService.getMultiSelection('versions'),
            }
        }).then(function (response) {
            console.log(endpointService);

            let data = response.data;
            let firstVersion = data[0];
            let lastVersion = data[data.length - 1];

            console.log(lastVersion);

            endpointService.info.code_change_version = lastVersion.version;
            endpointService.info.code_change_versions_ago = data.length;

            let changed_endpoints = lastVersion.changed_endpoints
            endpointService.info.endpoints_changed = changed_endpoints;

            let execution_time_change = firstVersion.median - lastVersion.median;
            endpointService.info.execution_time_change = execution_time_change;

            let deviation = lastVersion.standard_deviation;
            endpointService.info.standard_deviation = deviation;

            let significant_slowdown = (execution_time_change > deviation);
            let endpoint_name = endpointService.info.name;
            let endpoint_changed = changed_endpoints.includes(endpoint_name);
            if (significant_slowdown && endpoint_changed) {
                endpointService.info.regression = "Yes";
            } else {
                endpointService.info.regression = "No";
            }

            plotlyService.chart(response.data.map(row => {
                return {
                    x: row.values,
                    type: 'box',
                    name: row.version + '<br>' + ($filter('dateLayout')(row.date)),
                    marker: { color: row.color }
                };
            }), {
                xaxis: {
                    title: 'Execution time (ms)',
                },
                yaxis: {
                    type: 'category',
                    autorange: 'reversed'
                },
                margin: {
                    l: 200
                }
            });
        });
    });
}