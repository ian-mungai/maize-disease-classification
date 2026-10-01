@extends('layouts.dashboard-app')

@section('content')
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-12">
                <a href="roles/create" class="btn btn-primary mb-2">Create Role </a>
                <br>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Role ID</th>
                            <th>Role</th>
                            <th colspan="2">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach ($roles as $role)
                            <tr>
                                <td>{{ $role->roleId }}</td>
                                <td>{{ $role->roleName }}</td>
                                <td>
                                    <a href="roles/{{ $role->roleId }}/edit" class="btn btn-primary">Edit</a>
                                    <form action="roles/{{ $role->roleId }}" method="post" class="d-inline">
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
