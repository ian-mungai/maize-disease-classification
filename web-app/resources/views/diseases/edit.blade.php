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
                                <label for="diseaseName">Disease Name</label>
                                <select name="diseaseName" id="diseaseName" class="form-control">
                                    @foreach ($names as $name)
                                        <option value="{{ $name }}" @selected(old('diseaseName', $disease->diseaseName ?? null) === $name)>{{ $name }}</option>
                                    @endforeach
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="">Recommendation</label>
                                <textarea name="recommendation" id="recommendation" cols="30" rows="10"
                                    class="form-control">{{ old('recommendation', $disease->recommendation) }}</textarea>
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
