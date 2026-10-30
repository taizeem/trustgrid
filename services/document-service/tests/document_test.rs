use document_service::validator::{FileValidator, MAX_FILE_SIZE};

#[test]
fn test_sniff_valid_pdf() {
    let pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF";
    let mime = FileValidator::sniff_mime_type(pdf_bytes).expect("Valid PDF magic bytes must succeed");
    assert_eq!(mime, "application/pdf");
}

#[test]
fn test_sniff_valid_png() {
    let png_bytes = &[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00];
    let mime = FileValidator::sniff_mime_type(png_bytes).expect("Valid PNG magic bytes must succeed");
    assert_eq!(mime, "image/png");
}

#[test]
fn test_sniff_valid_jpeg() {
    let jpeg_bytes = &[0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46];
    let mime = FileValidator::sniff_mime_type(jpeg_bytes).expect("Valid JPEG magic bytes must succeed");
    assert_eq!(mime, "image/jpeg");
}

#[test]
fn test_sniff_plain_text() {
    let text_bytes = b"This is a legitimate plain text compliance evidence document.\nSecond line.\n";
    let mime = FileValidator::sniff_mime_type(text_bytes).expect("Valid ASCII plain text must succeed");
    assert_eq!(mime, "text/plain");
}

#[test]
fn test_reject_executable_pe() {
    // Windows PE Executable magic header (MZ)
    let exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00";
    let result = FileValidator::sniff_mime_type(exe_bytes);
    assert!(result.is_err(), "Executable file disguised as document must be rejected");
}

#[test]
fn test_reject_elf_binary() {
    // Linux ELF header (0x7F 'E' 'L' 'F')
    let elf_bytes = &[0x7F, 0x45, 0x4C, 0x46, 0x02, 0x01, 0x01, 0x00];
    let result = FileValidator::sniff_mime_type(elf_bytes);
    assert!(result.is_err(), "ELF binary file must be rejected");
}

#[test]
fn test_reject_too_small() {
    let tiny_bytes = b"ab";
    let result = FileValidator::sniff_mime_type(tiny_bytes);
    assert!(result.is_err(), "Files smaller than 4 bytes must be rejected");
}

#[test]
fn test_max_file_size_constant() {
    assert_eq!(MAX_FILE_SIZE, 10 * 1024 * 1024);
}