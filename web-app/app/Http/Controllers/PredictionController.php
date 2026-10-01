<?php

namespace App\Http\Controllers;

use Auth;
use App\Models\Prediction;
use App\Models\Disease;
use Illuminate\Http\Request;
use GuzzleHttp\Client;
use Illuminate\Support\Facades\Log;

class PredictionController extends Controller
{
    public function __construct()
    {
        $this->middleware('auth');
    }

    public function index(Request $request)
    {
        $user_id = Auth::user()->userId;
        $predictions = Prediction::where('userId', $user_id)->get();

        return view('predictions.index', compact('predictions'))
            ->with('i', (request()->input('page', 1) - 1) * 5);
    }

    public function create()
    {
        return view('predictions.create');
    }

    public function store(Request $request)
    {
        $user_id = Auth::user()->userId;

        $request->validate([
            'image' => 'required|image|mimes:jpeg,png,jpg,gif,svg|max:2048',
        ]);

        $imageName = time().'.'.$request->image->extension();

        $request->image->move(public_path('images'), $imageName);

        $imagePath = public_path('images')."/".$imageName;

        $client = new Client();
        $img = fopen($imagePath, 'r');
        $url = "http://127.0.0.1:4040/disease-analyzer";

        $resp = $client->request('POST', $url , ['json'=> ['img' => $imagePath]]);

        $prediction = new Prediction();
        $prediction->description = $request->description;
        $prediction->imageName = $imageName;
        $prediction->userId = $user_id;
        $prediction->prediction =  $resp->getBody();

        $prediction->save();
        return redirect()->route('predictions.index')
        ->with('Success', 'Prediction successfull.');

    }

    public function show(Prediction $prediction)
    {
        $diseases = Disease::where('diseaseName', $prediction->prediction)->first();

        return view('predictions.show', compact('prediction','diseases'));
    }
}
