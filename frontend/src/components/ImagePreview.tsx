'use client';

interface Props {
  src: string;
  alt: string;
  label: string;
}

export default function ImagePreview({ src, alt, label }: Props) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-2">{label}</h3>
      <div className="relative aspect-video bg-gray-100 rounded overflow-hidden">
        <img
          src={src}
          alt={alt}
          className="absolute inset-0 w-full h-full object-contain"
        />
      </div>
    </div>
  );
}
