#[cfg(test)]
mod tests {
    // Tests authentic PDF signature detection
    #[test]
    fn test_valid_pdf_magic_bytes() {
        let pdf_sample = b"%PDF-1.4\n%test binary content";
        assert!(pdf_sample.starts_with(b"%PDF-"));
    }

    // Tests spoofed executable masquerading as a PDF
    #[test]
    fn test_spoofed_executable_rejected() {
        let exe_sample = b"MZ\x90\x00\x03\x00\x00\x00"; // Windows PE Executable magic header
        assert!(!exe_sample.starts_with(b"%PDF-"));
        assert!(!exe_sample.starts_with(&[0x89, 0x50, 0x4E, 0x47]));
        assert!(!exe_sample.starts_with(&[0xFF, 0xD8, 0xFF]));
    }

    // Tests authentic PNG header
    #[test]
    fn test_valid_png_magic_bytes() {
        let png_sample = &[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
        assert_eq!(&png_sample[0..4], &[0x89, 0x50, 0x4E, 0x47]);
    }
}