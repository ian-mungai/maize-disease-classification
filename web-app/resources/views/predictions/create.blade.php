@extends('layouts.dashboard-app')

@section('content')
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">{{ __('New Prediction') }}</div>

                    <div class="card-body">
                        @if (session('status'))
                            <div class="alert alert-success" role="alert">
                                {{ session('status') }}
                            </div>
                        @endif

                        <form action="/predictions" method="post" enctype="multipart/form-data">
                            @csrf
                            <div class="form-group">
                                <label for="">Description</label>
                                <input type="text" name="description" class="form-control">
                            </div>

                            <div class="form-group">
                                <label for="image">Image</label>
                                <input type="file" name="image" class="form-control">
                            </div>

                            <button type="submit" class="btn btn-primary">Upload</button>
                            <a class="btn btn-danger" href="{{ route('predictions.index') }}">Back</a>
                        </form>

                    </div>
                </div>
            </div>
        </div>
    </div>
@endsection
