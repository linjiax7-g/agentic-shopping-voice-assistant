import { useState, useEffect } from 'react';
import { Document, Page } from 'react-pdf';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  ChevronLeft, 
  ChevronRight, 
  ZoomIn, 
  ZoomOut, 
  Download,
  Loader2,
  AlertCircle,
  RotateCw
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface PDFViewerProps {
  fileUrl: string;
  fileName?: string;
  className?: string;
  showToolbar?: boolean;
  showDownload?: boolean;
  defaultZoom?: number;
  currentPage?: number;
  zoom?: number;
  onPageChange?: (page: number) => void;
  onLoadSuccess?: (numPages: number) => void;
  onLoadError?: (error: Error) => void;
}

export const PDFViewer = ({
  fileUrl,
  fileName = 'document.pdf',
  className,
  showToolbar = true,
  showDownload = true,
  defaultZoom = 100,
  currentPage: controlledPage,
  zoom: controlledZoom,
  onPageChange,
  onLoadSuccess,
  onLoadError,
}: PDFViewerProps) => {
  const [numPages, setNumPages] = useState<number>(0);
  const [internalPage, setInternalPage] = useState<number>(1);
  const [internalZoom, setInternalZoom] = useState<number>(defaultZoom);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  // Use controlled or internal state
  const pageNumber = controlledPage ?? internalPage;
  const scale = (controlledZoom ?? internalZoom) / 100;

  const setPageNumber = (page: number) => {
    if (onPageChange) {
      onPageChange(page);
    } else {
      setInternalPage(page);
    }
  };

  const handleDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
    setError(null);
    if (onLoadSuccess) {
      onLoadSuccess(numPages);
    }
  };

  const handleDocumentLoadError = (err: Error) => {
    setIsLoading(false);
    setError(err);
    if (onLoadError) {
      onLoadError(err);
    }
  };

  const handlePreviousPage = () => {
    if (pageNumber > 1) {
      setPageNumber(pageNumber - 1);
    }
  };

  const handleNextPage = () => {
    if (pageNumber < numPages) {
      setPageNumber(pageNumber + 1);
    }
  };

  const handleZoomIn = () => {
    if (controlledZoom === undefined) {
      setInternalZoom(prev => Math.min(prev + 25, 200));
    }
  };

  const handleZoomOut = () => {
    if (controlledZoom === undefined) {
      setInternalZoom(prev => Math.max(prev - 25, 50));
    }
  };

  const handleResetZoom = () => {
    if (controlledZoom === undefined) {
      setInternalZoom(100);
    }
  };

  const handleRestart = () => {
    setPageNumber(1);
    if (controlledZoom === undefined) {
      setInternalZoom(100);
    }
  };

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = fileUrl;
    a.download = fileName;
    a.click();
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (e.key) {
        case 'ArrowLeft':
          handlePreviousPage();
          break;
        case 'ArrowRight':
          handleNextPage();
          break;
        case '+':
        case '=':
          handleZoomIn();
          break;
        case '-':
          handleZoomOut();
          break;
        case '0':
          handleResetZoom();
          break;
        case 'Home':
          handleRestart();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pageNumber, numPages]);

  if (error) {
    return (
      <div className={cn("flex items-center justify-center h-full bg-muted rounded-lg p-8", className)}>
        <div className="text-center space-y-4 max-w-md">
          <AlertCircle className="w-12 h-12 mx-auto text-destructive" />
          <h4 className="font-semibold text-lg">Failed to Load PDF</h4>
          <p className="text-sm text-muted-foreground">{error.message}</p>
          <Button onClick={() => window.location.reload()} variant="outline">
            <RotateCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {showToolbar && (
        <div className="flex items-center justify-between gap-2 p-3 border-b bg-background">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviousPage}
              disabled={pageNumber <= 1 || isLoading}
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            
            <span className="text-sm text-muted-foreground min-w-[100px] text-center">
              {isLoading ? '...' : `Page ${pageNumber} of ${numPages}`}
            </span>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleNextPage}
              disabled={pageNumber >= numPages || isLoading}
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRestart}
              disabled={isLoading}
              aria-label="Restart to page 1"
              title="Restart (Home)"
            >
              <RotateCw className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomOut}
              disabled={scale <= 0.5 || isLoading}
              aria-label="Zoom out"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            
            <span className="text-sm text-muted-foreground min-w-[60px] text-center">
              {Math.round(scale * 100)}%
            </span>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleZoomIn}
              disabled={scale >= 2 || isLoading}
              aria-label="Zoom in"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>

            {showDownload && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                disabled={isLoading}
                aria-label="Download PDF"
              >
                <Download className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      )}

      <ScrollArea className="flex-1">
        <div className="flex items-center justify-center p-4 bg-muted/30 min-h-full">
          {isLoading && (
            <div className="flex flex-col items-center justify-center space-y-4">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading PDF...</p>
            </div>
          )}
          
          <Document
            file={fileUrl}
            onLoadSuccess={handleDocumentLoadSuccess}
            onLoadError={handleDocumentLoadError}
            loading={null}
            className={cn(isLoading && "hidden")}
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderTextLayer={false}
              renderAnnotationLayer={false}
              className="shadow-lg"
            />
          </Document>
        </div>
      </ScrollArea>
    </div>
  );
};
