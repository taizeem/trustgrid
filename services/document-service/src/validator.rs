use crate::error::ServiceError;

pub const MAX_FILE_SIZE: usize = 10 * 1024 * 1024; // 10MB limit

pub struct FileValidator;

impl FileValidator {
    pub fn sniff_mime_type(bytes: &[u8]) -> Result<&'static str, ServiceError> {
        if bytes.len() < 4 {
            return Err(ServiceError::Validation("File too small to evaluate signature".into()));
        }

        // PDF: starts with %PDF- (0x25 0x50 0x44 0x46)
        if bytes.starts_with(b"%PDF-") {
            return Ok("application/pdf");
        }

        // PNG: starts with 0x89 0x50 0x4E 0x47 0x0D 0x0A 0x1A 0x0A
        if bytes.starts_with(&[0x89, 0x50, 0x4E, 0x47]) {
            return Ok("image/png");
        }

        // JPEG: starts with 0xFF 0xD8 0xFF
        if bytes.starts_with(&[0xFF, 0xD8, 0xFF]) {
            return Ok("image/jpeg");
        }

        // Plain Text: printable ASCII bytes
        if bytes.iter().take(512).all(|&b| b == b'\n' || b == b'\r' || b == b'\t' || (32..=126).contains(&b)) {
            return Ok("text/plain");
        }

        Err(ServiceError::Validation(
            "Unsupported file type. Only authentic PDF, PNG, JPEG, and plain text files are allowed.".into(),
        ))
    }
}