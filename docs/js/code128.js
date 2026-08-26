/*
 * Code128 (Set B) encoder.
 *
 * The CODES/STOP/CHARSET_B tables below are copied verbatim from the
 * python-barcode library (the same library the desktop app uses), so this
 * produces genuine, standard, scannable Code128 barcodes - independently
 * verified by round-tripping through a Python decoder using the same
 * tables before this was wired into the page.
 *
 * Only Set B is implemented (covers space through ~, which is every
 * character our labels use - letters, digits, dashes, etc). Real Code128
 * encoders often switch between subsets A/B/C to shorten numeric runs;
 * skipping that optimization keeps this encoder simple and still produces
 * fully valid, scannable barcodes - just not always the shortest possible
 * encoding for very long all-numeric labels, which doesn't matter here
 * since bar width is normalized to a fixed block width anyway.
 */

const CODE128_CODES = [
  "11011001100","11001101100","11001100110","10010011000","10010001100","10001001100",
  "10011001000","10011000100","10001100100","11001001000","11001000100","11000100100",
  "10110011100","10011011100","10011001110","10111001100","10011101100","10011100110",
  "11001110010","11001011100","11001001110","11011100100","11001110100","11101101110",
  "11101001100","11100101100","11100100110","11101100100","11100110100","11100110010",
  "11011011000","11011000110","11000110110","10100011000","10001011000","10001000110",
  "10110001000","10001101000","10001100010","11010001000","11000101000","11000100010",
  "10110111000","10110001110","10001101110","10111011000","10111000110","10001110110",
  "11101110110","11010001110","11000101110","11011101000","11011100010","11011101110",
  "11101011000","11101000110","11100010110","11101101000","11101100010","11100011010",
  "11101111010","11001000010","11110001010","10100110000","10100001100","10010110000",
  "10010000110","10000101100","10000100110","10110010000","10110000100","10011010000",
  "10011000010","10000110100","10000110010","11000010010","11001010000","11110111010",
  "11000010100","10001111010","10100111100","10010111100","10010011110","10111100100",
  "10011110100","10011110010","11110100100","11110010100","11110010010","11011011110",
  "11011110110","11110110110","10101111000","10100011110","10001011110","10111101000",
  "10111100010","11110101000","11110100010","10111011110","10111101110","11101011110",
  "11110101110","11010000100","11010010000","11010011100",
];
const CODE128_STOP = "11000111010";
const CODE128_START_B = 104;

// Set B character order (index -> character), matching python-barcode's mapping.
const CODE128_CHARSET_B = (() => {
  const common = [
    " ", "!", '"', "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    ":", ";", "<", "=", ">", "?", "@",
  ];
  for (let c = 65; c <= 90; c++) common.push(String.fromCharCode(c)); // A-Z
  common.push("[", "\\", "]", "^", "_");
  const lower = [];
  for (let c = 97; c <= 122; c++) lower.push(String.fromCharCode(c)); // a-z
  return [...common, "`", ...lower, "{", "|", "}", "~"];
})();

const CODE128_B_INDEX = {};
CODE128_CHARSET_B.forEach((ch, i) => { CODE128_B_INDEX[ch] = i; });

/**
 * Encode text as a Code128 Set B module string ('1' = bar, '0' = space),
 * with the leading quiet zone omitted (matching python-barcode's
 * `code.build()[0]`, which sticky_signs_core.py / hanging_signs_core.py
 * both rely on) - callers add their own margin/quiet zone as page layout.
 */
function encodeCode128B(text) {
  const dataCodes = [];
  for (const ch of text) {
    if (!(ch in CODE128_B_INDEX)) {
      throw new Error(`Character ${JSON.stringify(ch)} can't be encoded in this barcode.`);
    }
    dataCodes.push(CODE128_B_INDEX[ch]);
  }

  const encoded = [CODE128_START_B, ...dataCodes];
  let checksum = encoded[0];
  for (let i = 1; i < encoded.length; i++) {
    checksum += i * encoded[i];
  }
  checksum %= 103;
  encoded.push(checksum);

  let pattern = "";
  for (const codeNum of encoded) {
    pattern += CODE128_CODES[codeNum];
  }
  pattern += CODE128_STOP;
  pattern += "11";
  return pattern;
}

if (typeof module !== "undefined") {
  module.exports = { encodeCode128B };
}
