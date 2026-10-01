<?php

namespace App\Http\Controllers;

use App\Models\Disease;
use App\Models\Prediction;
use Illuminate\Database\UniqueConstraintViolationException;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\ValidationException;

class PredictionController extends Controller
{
    private const IMAGE_DIR = 'leaf_images';

    public function __construct()
    {
        $this->middleware('auth');
    }

    public function index(Request $request)
    {
        $this->authorize('viewAny', Prediction::class);

        $predictions = $request->user()->predictions()->latest()->get();

        return view('predictions.index', compact('predictions'));
    }

    public function create()
    {
        $this->authorize('create', Prediction::class);

        return view('predictions.create');
    }

    /**
     * Classify an uploaded leaf image. Uploading the same image again returns the existing prediction
     * instead of calling the model or storing a duplicate.
     */
    public function store(Request $request)
    {
        $this->authorize('create', Prediction::class);

        $validated = $request->validate([
            'description' => ['nullable', 'string', 'max:255'],
            'image' => ['required', 'file', 'mimes:jpeg,jpg,png', 'max:2048'],
        ]);

        $user = $request->user();
        $image = $validated['image'];
        $contents = $image->get();
        $hash = hash('sha256', $contents);

        $existing = $user->predictions()->where('imageHash', $hash)->first();
        if ($existing) {
            return redirect()->route('predictions.show', $existing)
                ->with('Success', 'This image was already classified.');
        }

        $label = $this->classify($contents, $image->getClientOriginalName());

        $imageName = $hash.'.'.$image->extension();
        Storage::disk('local')->put(self::IMAGE_DIR.'/'.$imageName, $contents);

        try {
            $prediction = new Prediction([
                'description' => $validated['description'] ?? '',
                'imageName' => $imageName,
                'imageHash' => $hash,
                'prediction' => $label,
            ]);
            $prediction->userId = $user->userId;
            $prediction->save();
        } catch (UniqueConstraintViolationException) {
            $prediction = $user->predictions()->where('imageHash', $hash)->firstOrFail();
        }

        return redirect()->route('predictions.show', $prediction)
            ->with('Success', 'Prediction successful.');
    }

    public function show(Prediction $prediction)
    {
        $this->authorize('view', $prediction);

        $disease = $prediction->disease;

        return view('predictions.show', compact('prediction', 'disease'));
    }

    public function image(Prediction $prediction)
    {
        $this->authorize('view', $prediction);

        return Storage::disk('local')->response(self::IMAGE_DIR.'/'.$prediction->imageName);
    }

    /**
     * Send the image bytes to the Flask model service and return a known class name.
     */
    private function classify(string $contents, string $fileName): string
    {
        try {
            $response = Http::timeout(30)
                ->attach('image', $contents, $fileName)
                ->post(config('services.maize_model.url'));
        } catch (ConnectionException $e) {
            Log::error('Model service unreachable', ['error' => $e->getMessage()]);
            throw ValidationException::withMessages(['image' => 'The prediction service is unavailable. Try again later.']);
        }

        $label = $response->json('prediction');
        if (! $response->ok() || ! in_array($label, Disease::NAMES, true)) {
            Log::error('Model service returned an unexpected response', ['status' => $response->status()]);
            throw ValidationException::withMessages(['image' => $response->json('error') ?? 'The image could not be classified.']);
        }

        return $label;
    }
}
