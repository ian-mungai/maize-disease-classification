@extends('layouts.dashboard-app')

@section('content')
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">{{ __('View Prediction') }}</div>

                    <div class="card-body">
                        @if (session('status'))
                            <div class="alert alert-success" role="alert">
                                {{ session('status') }}
                            </div>
                        @endif
                        <div>
                            <b>Description : </b>{{ $prediction->description }}
                            <br>
                            <b>Prediction : </b><span id="prediction">{{ $prediction->prediction }}</span>
                        </div>
                        <br>
                        <div>
                            <img src="{{ route('predictions.image', $prediction) }}" alt="Uploaded maize leaf" style="max-width: 600px; max-height: 400px;" />
                        </div>
                        <br>
                        <div>
                            <b>Recommendation : </b><br><span id="recommendation">{{ $disease?->recommendation ?? 'No recommendation has been added for this class yet.' }}</span>
                        </div>

                    </div>
                </div><br>
                <a class="btn btn-danger" href="{{ route('predictions.index') }}">Back</a>
            </div>
        </div>
    </div>
@endsection
