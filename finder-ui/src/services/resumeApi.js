export const getResume = async (options = {}) => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), options.timeout || 15000);
    try {
        const res = await fetch('/api/resume', { 
            signal: options.signal || controller.signal 
        });
        clearTimeout(id);
        return await res.json();
    } catch (e) {
        clearTimeout(id);
        if (e.name === 'AbortError') throw new Error('Request timed out');
        throw e;
    }
};

export const uploadResume = (file, onProgress, options = {}) => {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    let timeoutId;

    const promise = new Promise((resolve, reject) => {
        const cleanup = () => {
            clearTimeout(timeoutId);
        };

        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable && onProgress) {
                const percentComplete = Math.round((event.loaded / event.total) * 100);
                onProgress(percentComplete);
            }
        });

        xhr.addEventListener('load', () => {
            cleanup();
            try {
                const response = JSON.parse(xhr.responseText);
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(response);
                } else {
                    reject(new Error(response.error?.message || 'Upload failed'));
                }
            } catch (error) {
                reject(new Error('Invalid response from server'));
            }
        });

        xhr.addEventListener('error', () => { cleanup(); reject(new Error('Network error')); });
        xhr.addEventListener('abort', () => { cleanup(); reject(new Error('Upload cancelled')); });

        timeoutId = setTimeout(() => {
            xhr.abort();
            reject(new Error('Upload timed out. Please try again.'));
        }, options.timeout || 30000);

        xhr.open('POST', '/api/resume', true);
        xhr.send(formData);
    });

    return { promise, abort: () => xhr.abort() };
};

export const deleteResume = async () => {
    const res = await fetch('/api/resume', { method: 'DELETE' });
    return res.json();
};
