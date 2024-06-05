// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { useNavigate } from 'react-router-dom';
import React, { useState, useEffect, useRef } from 'react';
import AWS from 'aws-sdk';
import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import NavDropdown from 'react-bootstrap/NavDropdown';
import 'bootstrap/dist/css/bootstrap.min.css';
import Form from 'react-bootstrap/Form';
import Button from 'react-bootstrap/Button';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import { v4 as uuidv4 } from 'uuid';
import Card from 'react-bootstrap/Card';
import Tab from 'react-bootstrap/Tab';
import Tabs from 'react-bootstrap/Tabs';
import InputGroup from 'react-bootstrap/InputGroup';
import Modal from 'react-bootstrap/Modal';

/*eslint-disable*/
function parseJwt(token) {
  var base64Url = token.split('.')[1];
  var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  var jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
  }).join(''));
  return JSON.parse(jsonPayload);
}

const HomePage = () => {
  const navigate = useNavigate();
  var idToken = parseJwt(sessionStorage.idToken.toString());
  var accessToken = parseJwt(sessionStorage.accessToken.toString());
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [finding, setFinding] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [requestQuery, setRequestQuery] = useState('');
  const [deleteQuery, setDeleteQuery] = useState('');
  const [email, setEmail] = useState('');
  const [filePreview, setFilePreview] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const fileInputRef = useRef(null); // Create a ref for the file input

  // @todo remove below - only for testing
  const [originalUrl, setOriginalUrl] = useState('');
  const [thumbnailUrl, setThumbnailUrl] = useState('');

  const [tags, setTags] = useState('');
  const [action, setAction] = useState('add');

  const [searchTags, setSearchTags] = useState('');
  const [imageGeneratedTags, setImageGeneratedTags] = useState('');
  const [searchTagsResultThumbnail, setsearchTagsResultThumbnail] = useState('');
  const [searchTagsResultFullsize, setsearchTagsResultFullsize] = useState('');
  const [searchTagsResultThumbnailUnpresigned, setsearchTagsResultThumbnailUnpresigned] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [currentImage, setCurrentImage] = useState('');

  const API_GATEWAY_URL_UPLOAD = "https://oa7cg4avwe.execute-api.us-east-1.amazonaws.com/a3-1/UploadImageToS3"; 
  const API_GATEWAY_URL_SEARCH = "https://oa7cg4avwe.execute-api.us-east-1.amazonaws.com/a3-1/image-handler"; 
  const API_GATEWAY_OBJECT_DETECT = "https://oa7cg4avwe.execute-api.us-east-1.amazonaws.com/a3-1/object-detection";
  const API_GATEWAY_SUBSCRIBE = "https://oa7cg4avwe.execute-api.us-east-1.amazonaws.com/a3-1/notification_handler";// Replace with your API Gateway URL
  
  const [labelCounts, setLabelCounts] = useState({});

  useEffect(() => {
    if (imageGeneratedTags) {
      handleSearchByTags(true);  // Call with fromImg=true
    }
  }, [imageGeneratedTags]);

  useEffect(() => {
    const idToken = parseJwt(sessionStorage.idToken.toString());
    if (idToken && idToken.email) {
      setEmail(idToken.email);
    }
    console.log("Access Token:", accessToken); // Log the access token for debugging

  }, []);

  const handleLogout = () => {
    sessionStorage.clear();
    navigate('/login');
  };
  /*eslint-enable*/

  const handleFileChange = (event) => {
    const allowedTypes = [
      'image/jpeg',
      'image/png',
      'image/jpg',
      // Add more supported types as needed
    ];

    const selectedFile = event.target.files[0];
    if (allowedTypes.includes(selectedFile.type)) {
      setFile(selectedFile);
      setFilePreview(URL.createObjectURL(selectedFile));
    } else {
      alert('Invalid file type. Only images and PDFs are allowed.');
    }
  };

  const removeFile = () => {
    setFile(null);
    setFilePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = ''; // Reset the file input value
    }
  };


  const uploadFile = async () => {
    if (!file) {
      alert('Please select a file to upload.');
      return;
    }

    setUploading(true);

    try {
      // Convert the file to a base64 string
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = async () => {
        const base64Data = reader.result?.toString().split(',')[1]; // Remove the data URL prefix
        const fileExtension = file.name.split('.').pop();
        const payload = {
          image_data: base64Data,
          // file_name: file.name
          file_name: `${uuidv4()}.${fileExtension}`, // 生成带扩展名的 UUID 文件名
          user_email: email
        };

        try {
          const response = await fetch(API_GATEWAY_URL_UPLOAD, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${sessionStorage.idToken}`, // Add the idToken to the request headers
            },
            body: JSON.stringify(payload),
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const response_obj = await response.json();
          console.log(response_obj);
          // Parse the nested JSON string
          const object_detection_result = JSON.parse(response_obj.object_detection_result.body);
          setThumbnailUrl(object_detection_result.object_detection_result.S3URL_Thumbnail);

          const Tags = object_detection_result.object_detection_result.Tags;

          const newLabelCounts = {};
          Tags.forEach(tag => {
            newLabelCounts[tag] = (newLabelCounts[tag] || 0) + 1;
          });

          setLabelCounts(newLabelCounts);

        } catch (error) {
          console.error("I guess it's CORS:", error);
        }
        setUploading(false);
        alert("File uploaded successfully.");
        removeFile();
      };

      reader.onerror = (error) => {
        console.error('Error reading file:', error);
        setUploading(false);
        alert("Error reading file: " + error);
      };
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploading(false);
      alert("Error uploading file: " + error.message);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery) {
      alert('Please enter an url to search.');
      return;
    }

    // Validate the URL format
    const resizedBucket = 'tan-image-bucket-resized';
    const originalBucket = 'tan-image-bucket';
    const resizedUrlPattern = new RegExp(`^https://${resizedBucket}.s3.amazonaws.com/resized-[a-f0-9-]+\.(jpg|jpeg|png|gif|bmp|tiff|webp)$`);

    if (!resizedUrlPattern.test(searchQuery)) {
      alert('Please enter a valid thumbnail\'s URL.');
      return;
    }

    const originalUrl = searchQuery.replace(`${resizedBucket}.s3.amazonaws.com/resized-`, `${originalBucket}.s3.amazonaws.com/`);


    setDownloading(true);

    try {
      const payload = { url: originalUrl, email: email };

      const response = await fetch(API_GATEWAY_URL_SEARCH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionStorage.idToken}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        setOriginalUrl(null);
        setImageUrl(null);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      else {
        // Set the original URL state
        setOriginalUrl(originalUrl);
      }
      const data = await response.json();
      console.log(data);
      setImageUrl(data.presigned_url);
    } catch (error) {
      console.error('Error fetching pre-signed URL:', error);
    } finally {
      setDownloading(false);

    }
  };

  const modifyTags = async (type) => {
    if (!requestQuery || !tags) {
      alert('Please enter a valid URL and tags.');
      return;
    }

    const urlsArray = requestQuery.split(',').map(url => url.trim());
    const tagsArray = tags.split(',').map(tag => tag.trim());

    const payload = {
      url: urlsArray,
      type: type, // 1 for add, 0 for remove
      tags: tagsArray,
      email: email
    };

    try {
      const response = await fetch(API_GATEWAY_URL_SEARCH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionStorage.idToken}`, // Add the idToken to the request headers
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      alert('Tags modified successfully.');
      console.log(data);
    } catch (error) {
      console.error('Error modifying tags:', error);
      alert('Error modifying tags: ' + error.message);
    }
  };

  const handleImageClick = (url) => {
    setCurrentImage(url);
    setShowModal(true);
  };
  const handleSearchByTags = async (fromImg = false) => {
    let tagsToSearch = fromImg ? imageGeneratedTags : searchTags;

    if (!tagsToSearch) {
      alert('Please enter tags or upload image to search.');
      return;
    }

    // Validate the tags format if it is from user input
    if (!fromImg) {
      const tagsPattern = new RegExp(`^([a-zA-Z0-9]+,[0-9]+,)*[a-zA-Z0-9]+,[0-9]+$`);
      if (!tagsPattern.test(tagsToSearch)) {
        alert('Please enter a valid tags format.');
        return;
      }
    }
    //构造请求的 tags
    const tags = tagsToSearch.split(",");
    const tagsDict = {};
    for (let i = 0; i < tags.length; i += 2) {
      tagsDict[tags[i]] = tags[i + 1];
    }
    console.log(tagsDict);
    setDownloading(true);
    //发起请求
    try {
      const payload = { tags: tagsDict, email: email };

      const response = await fetch(API_GATEWAY_URL_SEARCH, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionStorage.idToken}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        alert('No image found.');
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      if (data.thumbnail_urls.length == 0) {
        alert('No image found.');
      }
      console.log("images:", data.thumbnail_urls);
      setsearchTagsResultThumbnail(data.thumbnail_urls);
      setsearchTagsResultFullsize(data.fullsize_urls);
      console.log("result", searchTagsResultThumbnail);
      setsearchTagsResultThumbnailUnpresigned(data.thumbnail_urls_unpresigned);
    } catch (error) {
      console.error('Error fetching pre-signed URL:', error);
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteQuery) {
      alert('Please enter valid URLs.');
      return;
    }

    const urlsArray = deleteQuery.split(',').map(url => url.trim());

    const payload = {
      url: urlsArray,
      email: email
    };

    try {
      const response = await fetch(API_GATEWAY_URL_SEARCH, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sessionStorage.idToken}`, // Add the idToken to the request headers
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      alert('Images deleted successfully.');
      console.log(data);
    } catch (error) {
      console.error('Error deleting images:', error);
      alert('Error deleting images: ' + error.message);
    }
  };

  const handleSearchByImage = async () => {
    if (!file) {
      alert('Please select a file to upload.');
      return;
    }

    setFinding(true);

    try {
      // Convert the file to a base64 string
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = async () => {
        const base64Data = reader.result?.toString().split(',')[1]; // Remove the data URL prefix
        const fileExtension = file.name.split('.').pop();
        const payload = {
          image_data: base64Data,
          // file_name: file.name
          file_name: `${uuidv4()}.${fileExtension}`, // 生成带扩展名的 UUID 文件名
          user_email: email
        };

        try {
          const response = await fetch(API_GATEWAY_OBJECT_DETECT, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${sessionStorage.idToken}`, // Add the idToken to the request headers
            },
            body: JSON.stringify(payload),
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const response_obj = await response.json();
          console.log("response_obj---", response_obj.object_detection_result.Tags);
          // Parse the nested JSON string
          // const object_detection_result = JSON.parse(response_obj.object_detection_result);

          const Tags = response_obj.object_detection_result.Tags;

          const newLabelCounts = {};
          Tags.forEach(tag => {
            newLabelCounts[tag] = (newLabelCounts[tag] || 0) + 1;
          });

          const formattedString = Object.entries(newLabelCounts)
            .map(([key, value]) => `${key},${value}`)
            .join(',');

          setLabelCounts(newLabelCounts);
          setImageGeneratedTags(formattedString);

        } catch (error) {
          console.error("I guess it's CORS:------------", error);
        }
        setFinding(false);
        // removeFile();
      };

      reader.onerror = (error) => {
        console.error('Error reading file:', error);
        setUploading(false);
        alert("Error reading file: " + error);
      };
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploading(false);
      alert("Error uploading file: " + error.message);
    }
  };

  const handleSubscribe = async (event) => {
    event.preventDefault();
    const tags = event.target.elements.tags.value;

    try {
      const response = await fetch(API_GATEWAY_SUBSCRIBE, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, tags }),
      });

      if (response.ok) {
        alert('Subscription successful!');
      } else {
        alert('Subscription failed.');
      }
    } catch (error) {
      console.error('Error subscribing to notifications:', error);
      alert('Error subscritags_query.items()bing to notifications: ' + error.message);
    }
  };


  return (
    <div className="page-container">
      <Container fluid>
        <Row>
          <Col>
            <Tabs
              defaultActiveKey="home"
              id="uncontrolled-tab-example"
              className="mb-3"
              fill
            >
              <Tab eventKey="home" title="Upload Image">
                <Card>
                  <Card.Body>
                    <h3>Select the image from your device below</h3>
                    <hr />
                    <div className="file-upload-container">
                      {filePreview && (
                        <img src={filePreview} alt="Preview" className="file-preview" />
                      )}
                      <div className="file-input-container">
                        <input ref={fileInputRef} type="file" required onChange={handleFileChange} />
                        <Button variant="outline-success" onClick={uploadFile} disabled={uploading}>{uploading ? 'Uploading...' : 'Upload Image'}</Button>
                        <Button variant="outline-danger" onClick={removeFile} disabled={!file || uploading}>Remove Image</Button>
                      </div>
                    </div>
                    {thumbnailUrl && <hr />}
                    <div>
                      <h5>{Object.keys(labelCounts).length > 0 ? "Object Detection Result" : ""}</h5>
                      {Object.entries(labelCounts).map(([label, count]) => (
                        <li key={label}>{label}: {count.toString()}</li>
                      ))}
                      {thumbnailUrl && `thumbnailUrl: ${thumbnailUrl}`}
                    </div>
                  </Card.Body>
                </Card>
              </Tab>
              <Tab eventKey="findimage" title="Get Original Image">
                <Card>
                  <Card.Body>
                    <h3>Get original image by entering quiries below</h3>
                    <hr />
                    <InputGroup className="mb-3">
                      <Form.Control
                        placeholder="Enter Queries"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                      />
                      <Button variant="outline-secondary" style={{ margin: "0" }} onClick={handleSearch} disabled={downloading}>
                        {downloading ? 'Searching...' : 'Search'}
                      </Button>
                    </InputGroup>
                    {imageUrl && <img src={imageUrl} alt="Fetched from S3" />}
                    <hr />
                    {originalUrl && <p>Original URL: <a href={originalUrl} target="_blank" rel="noopener noreferrer">{originalUrl}</a></p>}
                    {imageUrl && <p>Presigned URL: <a href={imageUrl} target="_blank" rel="noopener noreferrer">{imageUrl}</a></p>}

                  </Card.Body>
                </Card>
              </Tab>
              <Tab eventKey="deleteimage" title="Delete Image">
                <Card>
                  <Card.Body>
                    <h3>Delete the image by entering quiries below</h3>
                    <hr />
                    <InputGroup className="mb-3">
                      <Form.Control
                        placeholder="Enter Queries"
                        value={deleteQuery}
                        onChange={(e) => setDeleteQuery(e.target.value)}
                      />
                      <Button variant="outline-danger" style={{ margin: "0" }} onClick={handleDelete} disabled={deleting}>
                        {deleting ? 'Deleting...' : 'Delete'}
                      </Button>
                    </InputGroup>
                    <hr />
                  </Card.Body>
                </Card>
              </Tab>
              <Tab eventKey="findimagebytags" title="Find Image By Tags / Image">
                <Card>
                  <Card.Body>
                    <h3>Find Image By Tags / Image</h3>
                    <hr />
                    <InputGroup className="mb-3">
                      <Form.Control
                        placeholder="Enter Queries follows the format: objectA,2,objectB,1"
                        value={searchTags}
                        onChange={(e) => setSearchTags(e.target.value)}
                      />
                      <Button variant="outline-secondary" style={{ margin: "0" }} onClick={() => handleSearchByTags(false)} disabled={downloading}>
                        {downloading ? 'Searching...' : 'Search'}
                      </Button>
                    </InputGroup>


                    <div className="file-input-container">
                      <input ref={fileInputRef} type="file" required onChange={handleFileChange} />
                      {filePreview && (
                        <img src={filePreview} alt="Preview" className="file-preview" />
                      )}
                      <Button variant="outline-primary" onClick={handleSearchByImage} disabled={uploading || finding}>{finding ? 'Finding...' : 'Find Image'}</Button>
                    </div>


                    {searchTagsResultThumbnail && <p>Thumbnail Contains Tags:</p>}
                    {Array.isArray(searchTagsResultThumbnail) && searchTagsResultThumbnail.map((url, index) => (
                      <div key={index} style={{ display: 'flex', alignItems: 'flex-end', margin: '10px 0' }}>
                        <img
                          src={url}
                          alt={`Image ${index}`}
                          style={{ marginRight: "10px", cursor: "pointer" }}
                          onClick={() => handleImageClick(searchTagsResultFullsize[index])}
                        />
                        <p style={{ margin: 0 }}>Thumbnail URL: {searchTagsResultThumbnailUnpresigned[index]}</p>
                      </div>
                    ))}
                    <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
                      <Modal.Header closeButton>
                        <Modal.Title>Full Size Image</Modal.Title>
                      </Modal.Header>
                      <Modal.Body>
                        <img src={currentImage} alt="Full Size" style={{ width: '100%' }} />
                      </Modal.Body>
                    </Modal>
                  </Card.Body>
                </Card>
              </Tab>
              <Tab eventKey="modifytag" title="Modify Tag">
                <Card>
                  <Card.Body>
                    <h3>Modify tags by enter to below</h3>
                    <hr />
                    <InputGroup className="mb-3">
                      <Form.Control
                        placeholder="Enter Thumbnail URL (comma separated)"
                        value={requestQuery}
                        onChange={(e) => setRequestQuery(e.target.value)}
                      />
                    </InputGroup>
                    <InputGroup className="mb-3">
                      <Form.Control
                        placeholder="Enter tags (comma separated)"
                        value={tags}
                        onChange={(e) => setTags(e.target.value)}
                      />
                    </InputGroup>
                    <Button variant="outline-success" onClick={() => modifyTags(1)} disabled={downloading}>
                      Add Tags
                    </Button>
                    <Button variant="outline-danger" onClick={() => modifyTags(0)} disabled={downloading} style={{ marginLeft: '10px' }}>
                      Remove Tags
                    </Button>
                  </Card.Body>
                </Card>
              </Tab>
              <Tab eventKey="subscribe" title="Subscribe to Notifications">
                <Card>
                  <Card.Body>
                    <h3>Set Tag Notification Preferences</h3>
                    <hr />
                    <Form onSubmit={handleSubscribe}>
                      <Form.Group controlId="tags">
                        <Form.Label>Tags (comma separated):</Form.Label>
                        <Form.Control type="text" placeholder="Enter tags separated by commas" required />
                      </Form.Group>
                      <Button variant="outline-primary" type="submit">
                        Set Preferences
                      </Button>
                    </Form>
                  </Card.Body>
                </Card>
              </Tab>
            </Tabs>
          </Col>
        </Row>
      </Container>
      <Button className="logout-button" variant="outline-danger" onClick={handleLogout}>
        Logout
      </Button>
    </div>

  );
};

export default HomePage;