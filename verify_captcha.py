import os
import sys
from app import create_app
from app.utils import generate_captcha_image

# Create app context because generate_captcha_image might rely on current_app (though in this case it doesn't seem to heavily, but best practice if it accesses config)
# Actually, looking at the code, generate_captcha_image doesn't use current_app, but let's be safe.
# It imports current_app but doesn't use it in generate_captcha_image logic shown.

def verify_captcha():
    print("Generating sample captchas...")
    try:
        # Create output directory if it doesn't exist
        output_dir = "captcha_samples"
        os.makedirs(output_dir, exist_ok=True)

        for i in range(5):
            code, image_io = generate_captcha_image()
            filename = os.path.join(output_dir, f"sample_{i}_{code}.png")
            
            with open(filename, "wb") as f:
                f.write(image_io.getvalue())
            
            print(f"Generated: {filename} (Code: {code})")
            
        print("Verification successful: 5 samples generated.")
    except Exception as e:
        print(f"Verification FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_captcha()
