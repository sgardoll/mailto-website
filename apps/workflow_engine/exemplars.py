"""Kind-specific Alpine v3 + Tailwind v3 exemplar HTML strings injected into BUILD prompts."""
from __future__ import annotations

CALCULATOR_EXEMPLAR: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>BMI Calculator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
  <div class="bg-white rounded-2xl shadow-md p-8 w-full max-w-sm"
       x-data="{ weight: '', height: '', bmi: null, category: '' }"
  >
    <h1 class="text-2xl font-bold text-gray-800 mb-6">BMI Calculator</h1>

    <label class="block text-sm font-medium text-gray-600 mb-1">Weight (kg)</label>
    <input type="number" x-model="weight" @input="bmi = null"
           class="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-400"
           min="1" max="500" aria-label="Weight in kilograms" />

    <label class="block text-sm font-medium text-gray-600 mb-1">Height (cm)</label>
    <input type="number" x-model="height" @input="bmi = null"
           class="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-400"
           min="50" max="300" aria-label="Height in centimetres" />

    <button
      @click="
        const w = parseFloat(weight);
        const h = parseFloat(height) / 100;
        if (w > 0 && h > 0) {
          bmi = (w / (h * h)).toFixed(1);
          if (bmi < 18.5) category = 'Underweight';
          else if (bmi < 25) category = 'Normal weight';
          else if (bmi < 30) category = 'Overweight';
          else category = 'Obese';
        }
      "
      class="w-full bg-blue-600 text-white font-semibold rounded-lg py-2 hover:bg-blue-700 transition"
    >Calculate</button>

    <template x-if="bmi !== null">
      <div class="mt-6 p-4 bg-blue-50 rounded-xl text-center">
        <p class="text-3xl font-bold text-blue-700" x-text="bmi"></p>
        <p class="text-sm text-gray-600 mt-1" x-text="category"></p>
      </div>
    </template>
  </div>
</body>
</html>"""


WIZARD_EXEMPLAR: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Profile Setup Wizard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
  <div class="bg-white rounded-2xl shadow-md p-8 w-full max-w-md"
       x-data="{ step: 1, name: '', email: '', role: '', submitted: false }"
  >
    <div class="mb-6">
      <p class="text-xs text-gray-400 font-medium uppercase tracking-wide mb-1">Step <span x-text="step"></span> of 2</p>
      <div class="w-full bg-gray-200 rounded-full h-2">
        <div class="bg-blue-600 h-2 rounded-full transition-all duration-300"
             :style="'width: ' + (step === 1 ? '50' : '100') + '%'"></div>
      </div>
    </div>

    <div x-show="step === 1">
      <h2 class="text-xl font-bold text-gray-800 mb-4">Your Details</h2>
      <label class="block text-sm font-medium text-gray-600 mb-1">Full name</label>
      <input type="text" x-model="name" aria-label="Full name"
             class="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-400" />
      <label class="block text-sm font-medium text-gray-600 mb-1">Email address</label>
      <input type="email" x-model="email" aria-label="Email address"
             class="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-400" />
      <button @click="step = 2"
              :disabled="!name || !email"
              class="w-full bg-blue-600 text-white font-semibold rounded-lg py-2 hover:bg-blue-700 transition disabled:opacity-50">
        Next
      </button>
    </div>

    <div x-show="step === 2">
      <h2 class="text-xl font-bold text-gray-800 mb-4">Your Role</h2>
      <label class="block text-sm font-medium text-gray-600 mb-1">Select your role</label>
      <select x-model="role" aria-label="Select your role"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-blue-400">
        <option value="">-- choose --</option>
        <option value="student">Student</option>
        <option value="teacher">Teacher</option>
        <option value="professional">Professional</option>
      </select>
      <div class="flex gap-3">
        <button @click="step = 1"
                class="flex-1 border border-gray-300 text-gray-700 font-semibold rounded-lg py-2 hover:bg-gray-50 transition">
          Back
        </button>
        <button @click="submitted = true" :disabled="!role"
                class="flex-1 bg-blue-600 text-white font-semibold rounded-lg py-2 hover:bg-blue-700 transition disabled:opacity-50">
          Submit
        </button>
      </div>
    </div>

    <template x-if="submitted">
      <div class="mt-6 p-4 bg-green-50 rounded-xl text-center">
        <p class="text-green-700 font-semibold">Profile saved!</p>
        <p class="text-sm text-gray-500 mt-1" x-text="name + ' · ' + role"></p>
      </div>
    </template>
  </div>
</body>
</html>"""


DRILL_EXEMPLAR: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Flashcard Drill</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
  <div class="bg-white rounded-2xl shadow-md p-8 w-full max-w-sm text-center"
       x-data="{
         cards: [
           { q: 'What is the powerhouse of the cell?', a: 'The mitochondria' },
           { q: 'What planet is closest to the Sun?', a: 'Mercury' },
           { q: 'What is H2O commonly known as?', a: 'Water' }
         ],
         index: 0,
         revealed: false,
         score: 0,
         done: false
       }"
  >
    <template x-if="!done">
      <div>
        <p class="text-xs text-gray-400 uppercase tracking-wide mb-2">
          Card <span x-text="index + 1"></span> of <span x-text="cards.length"></span>
        </p>
        <div class="bg-blue-50 rounded-xl p-6 mb-6 min-h-24 flex items-center justify-center">
          <p class="text-lg font-semibold text-gray-800" x-text="cards[index].q"></p>
        </div>

        <div x-show="revealed" class="mb-4 p-4 bg-green-50 rounded-xl">
          <p class="text-green-700 font-medium" x-text="cards[index].a"></p>
        </div>

        <button x-show="!revealed" @click="revealed = true"
                class="w-full bg-blue-600 text-white font-semibold rounded-lg py-2 hover:bg-blue-700 transition mb-3">
          Reveal Answer
        </button>

        <div x-show="revealed" class="flex gap-3">
          <button @click="index++; revealed = false; if (index >= cards.length) done = true"
                  class="flex-1 border border-red-300 text-red-600 rounded-lg py-2 hover:bg-red-50 transition">
            Missed
          </button>
          <button @click="score++; index++; revealed = false; if (index >= cards.length) done = true"
                  class="flex-1 bg-green-600 text-white rounded-lg py-2 hover:bg-green-700 transition">
            Got it
          </button>
        </div>
      </div>
    </template>

    <template x-if="done">
      <div class="text-center">
        <p class="text-2xl font-bold text-gray-800 mb-2">Session complete!</p>
        <p class="text-gray-500">Score: <span class="font-bold text-blue-600" x-text="score + ' / ' + cards.length"></span></p>
        <button @click="index = 0; revealed = false; score = 0; done = false"
                class="mt-6 w-full bg-blue-600 text-white font-semibold rounded-lg py-2 hover:bg-blue-700 transition">
          Restart
        </button>
      </div>
    </template>
  </div>
</body>
</html>"""


SCORER_EXEMPLAR: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Rubric Scorer</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
  <div class="bg-white rounded-2xl shadow-md p-8 w-full max-w-md"
       x-data="{
         clarity: 5,
         depth: 5,
         evidence: 5,
         get total() {
           return ((this.clarity * 0.3 + this.depth * 0.4 + this.evidence * 0.3) * 10).toFixed(0);
         },
         get grade() {
           const t = parseFloat(this.total);
           if (t >= 90) return 'A';
           if (t >= 80) return 'B';
           if (t >= 70) return 'C';
           if (t >= 60) return 'D';
           return 'F';
         }
       }"
  >
    <h1 class="text-2xl font-bold text-gray-800 mb-6">Rubric Scorer</h1>

    <div class="space-y-6">
      <div>
        <div class="flex justify-between text-sm font-medium text-gray-600 mb-1">
          <span>Clarity (30%)</span>
          <span x-text="clarity + '/10'"></span>
        </div>
        <input type="range" min="0" max="10" step="1" x-model="clarity" @input="$el.blur()"
               aria-label="Clarity score from 0 to 10"
               class="w-full accent-blue-600" />
      </div>

      <div>
        <div class="flex justify-between text-sm font-medium text-gray-600 mb-1">
          <span>Depth (40%)</span>
          <span x-text="depth + '/10'"></span>
        </div>
        <input type="range" min="0" max="10" step="1" x-model="depth" @input="$el.blur()"
               aria-label="Depth score from 0 to 10"
               class="w-full accent-blue-600" />
      </div>

      <div>
        <div class="flex justify-between text-sm font-medium text-gray-600 mb-1">
          <span>Evidence (30%)</span>
          <span x-text="evidence + '/10'"></span>
        </div>
        <input type="range" min="0" max="10" step="1" x-model="evidence" @input="$el.blur()"
               aria-label="Evidence score from 0 to 10"
               class="w-full accent-blue-600" />
      </div>
    </div>

    <div class="mt-8 p-5 bg-blue-50 rounded-xl flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-500 font-medium">Weighted Score</p>
        <p class="text-3xl font-bold text-blue-700" x-text="total + '/100'"></p>
      </div>
      <div class="text-center">
        <p class="text-sm text-gray-500 font-medium">Grade</p>
        <p class="text-4xl font-bold text-blue-600" x-text="grade"></p>
      </div>
    </div>
  </div>
</body>
</html>"""


GENERATOR_EXEMPLAR: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bio Generator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js" defer></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center p-4">
  <div class="bg-white rounded-2xl shadow-md p-8 w-full max-w-md"
       x-data="{ name: '', role: '', output: '' }"
  >
    <h1 class="text-2xl font-bold text-gray-800 mb-6">Bio Generator</h1>

    <label class="block text-sm font-medium text-gray-600 mb-1">Your name</label>
    <input type="text" x-model="name" @input="output = ''" aria-label="Your name"
           class="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-400" />

    <label class="block text-sm font-medium text-gray-600 mb-1">Your role or title</label>
    <input type="text" x-model="role" @input="output = ''" aria-label="Your role or title"
           class="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-blue-400" />

    <button
      @click="
        if (name.trim() && role.trim()) {
          output = name.trim() + ' is a passionate ' + role.trim() + ' committed to continuous learning and meaningful impact. With a focus on practical results, ' + name.trim() + ' brings clarity and creativity to every challenge.';
        }
      "
      :disabled="!name.trim() || !role.trim()"
      class="w-full bg-blue-600 text-white font-semibold rounded-lg py-2 hover:bg-blue-700 transition disabled:opacity-50"
    >Generate Bio</button>

    <template x-if="output">
      <div class="mt-6 p-4 bg-blue-50 rounded-xl">
        <p class="text-sm text-gray-700 leading-relaxed" x-text="output"></p>
        <button @click="
                  navigator.clipboard.writeText(output).catch(function() {});
                "
                class="mt-3 text-xs text-blue-600 hover:underline font-medium">
          Copy to clipboard
        </button>
      </div>
    </template>
  </div>
</body>
</html>"""
