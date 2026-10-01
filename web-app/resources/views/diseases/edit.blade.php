@extends('layouts.dashboard-app')

@section('content')
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">{{ __('Edit Disease') }}</div>

                    <div class="card-body">
                        @if (session('status'))
                            <div class="alert alert-success" role="alert">
                                {{ session('status') }}
                            </div>
                        @endif

                        <form action="/diseases/{{ $disease->diseaseId }}" method="post">
                            @csrf
                            @method('PUT')
                            <div class="form-group">
                                <label for="">Disease Name</label>
                                <input type="text" name="diseaseName" class="form-control"
                                    value="{{ $disease->diseaseName }}">
                            </div>

                            <div class="form-group">
                                <label for="">Recommendation</label>
                                <textarea name="recommendation" id="recommendation" cols="30" rows="10"
                                    class="form-control">{{ $disease->recommendation }}</textarea>
                            </div>

                            <button type="submit" class="btn btn-primary">Update</button>
                            <a class="btn btn-danger" href="{{ route('diseases.index') }}">Back</a>
                        </form>

                    </div>
                </div>
            </div>
        </div>
    </div>
@endsection
