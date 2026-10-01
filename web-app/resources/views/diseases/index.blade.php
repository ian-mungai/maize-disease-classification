@extends('layouts.dashboard-app')

@section('content')
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-12">
                <a href="diseases/create" class="btn btn-primary mb-2">Create Disease</a>
                <br>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Disease ID</th>
                            <th>Disease Name</th>
                            <th>Recommendation</th>
                            <th colspan="2">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach ($diseases as $disease)
                            <tr>
                                <td>{{ $disease->diseaseId }}</td>
                                <td>{{ $disease->diseaseName }}</td>
                                <td>{{ $disease->recommendation }}</td>
                                <td>
                                    <a href="diseases/{{ $disease->diseaseId }}/edit" class="btn btn-primary">Edit</a>
                                    <form action="diseases/{{ $disease->diseaseId }}" method="post" class="d-inline">
                                        {{ csrf_field() }}
                                        @method('DELETE')
                                        <button class="btn btn-danger" type="submit">Delete</button>
                                    </form>
                                </td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </div>
    </div>
@endsection
