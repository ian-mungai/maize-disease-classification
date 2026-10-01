@extends('layouts.dashboard-app')

@section('content')
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-12">
                <a href="predictions/create" class="btn btn-primary mb-2">New Prediction</a>
                <br>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Prediction ID</th>
                            <th>Description</th>
                            <th>Prediction</th>
                            <th colspan="2">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach ($predictions as $prediction)
                            <tr>
                                <td>{{ $prediction->predictionId }}</td>
                                <td>{{ $prediction->description }}</td>
                                <td>{{ $prediction->prediction }}</td>
                                <td>
                                    <a href="predictions/{{ $prediction->predictionId }}" class="btn btn-primary">Show</a>
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </div>
    </div>
@endsection
